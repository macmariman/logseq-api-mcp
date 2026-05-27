"""Write a Logseq page directly to disk (file-mode graphs only).

Bypasses the HTTP API and atomically overwrites (or creates) the ``.md``
file for a page. This is dramatically faster than the per-block API path
when replacing an entire page's content.

Atomicity is guaranteed by writing to a temp file in the same directory
and then ``os.replace``-ing it onto the target. If anything fails mid-
write, the original file is untouched.

Concurrency note: this tool does not coordinate with the Logseq UI. If
Logseq is editing the same page in another process, the last writer
wins. Either close Logseq or avoid simultaneous edits during bulk fs
operations.
"""

import os
import tempfile
from pathlib import Path
from typing import List, Literal

from mcp.types import TextContent

from src.client.config import LogseqConfig
from src.client.logseq_client import LogseqClient
from src.fs.paths import resolve_page_path, target_path_for_write
from src.logging_setup import get_logger

_log = get_logger(__name__)

WriteMode = Literal["create", "overwrite", "upsert"]


def _atomic_write(target: Path, content: str) -> None:
    """Write ``content`` to ``target`` atomically via tempfile + os.replace.

    The tempfile is created in the same directory as ``target`` so the
    final rename stays on a single filesystem (POSIX guarantees atomicity
    only within one mount). On any error the tempfile is cleaned up and
    the original target is left intact.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
    )
    tmp = Path(tmp_path)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp, target)
    except BaseException:
        # Clean up the tempfile on any failure (including KeyboardInterrupt).
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise


async def _run(
    client: LogseqClient,
    config: LogseqConfig,
    page_name: str,
    content: str,
    mode: WriteMode = "overwrite",
) -> List[TextContent]:
    """Write a page to disk atomically.

    Args:
        client: Unused; kept for the standard tool signature.
        config: Provides ``graph_path`` and ``db_mode``.
        page_name: Page name as shown in Logseq.
        content: Full markdown content to write.
        mode: ``"create"`` fails if the page exists, ``"overwrite"``
            (default) fails if it does not, ``"upsert"`` accepts both.

    Returns:
        Single :class:`TextContent` summarising the write
        (path, bytes, effective action). On error, a ``❌``-prefixed message.

    Complexity: O(N) where N is len(content).
    """
    try:
        _log.debug("%s called: %r mode=%s", __name__, page_name, mode)

        if config.db_mode:
            return [
                TextContent(
                    type="text",
                    text="❌ fs_write_page is for file-mode graphs only "
                    "(LOGSEQ_DB_MODE=true is set).",
                )
            ]

        if not config.graph_path:
            return [
                TextContent(
                    type="text",
                    text="❌ LOGSEQ_GRAPH_PATH is not set. Point it at your "
                    "graph root (the folder containing pages/ and journals/).",
                )
            ]

        if mode not in ("create", "overwrite", "upsert"):
            return [
                TextContent(
                    type="text",
                    text=f"❌ Invalid mode {mode!r}. "
                    "Must be 'create', 'overwrite', or 'upsert'.",
                )
            ]

        existing = resolve_page_path(config.graph_path, page_name)

        if mode == "create" and existing is not None:
            return [
                TextContent(
                    type="text",
                    text=(
                        f"❌ Page already exists: {page_name!r} "
                        f"(at {existing}). Use mode='overwrite' or 'upsert'."
                    ),
                )
            ]
        if mode == "overwrite" and existing is None:
            return [
                TextContent(
                    type="text",
                    text=(
                        f"❌ Page not found: {page_name!r} "
                        "(searched pages/ and journals/). "
                        "Use mode='create' or 'upsert' to create it."
                    ),
                )
            ]

        if existing is not None:
            target = existing
            action = "overwritten"
        else:
            candidate = target_path_for_write(config.graph_path, page_name)
            if candidate is None:
                return [
                    TextContent(
                        type="text",
                        text=(
                            f"❌ Refusing to write outside graph root: {page_name!r}."
                        ),
                    )
                ]
            target = candidate
            action = "created"

        _atomic_write(target, content)

        size = len(content.encode("utf-8"))
        rel = target.relative_to(Path(config.graph_path).resolve())
        return [
            TextContent(
                type="text",
                text=(
                    f"✅ {action.capitalize()} {page_name!r} ({size} bytes)\n📁 {rel}"
                ),
            )
        ]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error writing page: {exc}")]


async def fs_write_page(
    client: LogseqClient,
    config: LogseqConfig,
    page_name: str,
    content: str,
    mode: WriteMode = "overwrite",
) -> List[TextContent]:
    """Atomically write a Logseq page's full markdown to disk (file-mode graphs only).

    Use this to replace an entire page in one I/O instead of many block-level
    API calls. Much faster than update_page for large rewrites.

    Args:
        page_name: Page name as it appears in Logseq (e.g. "My Page",
            "Project/Sub"). Journal entries use Logseq's default filename
            format ``yyyy_MM_dd`` (e.g. "2026_05_27"); custom journal
            formats are not auto-detected — create the file manually once
            and use mode="overwrite" afterwards.
        content: Full markdown content to write. Replaces any existing content.
        mode: "create" fails if the page exists; "overwrite" (default)
            fails if it doesn't; "upsert" accepts both.
    """
    # client/config are injected by the registry's adaptive binding.
    return await _run(client, config, page_name, content, mode)
