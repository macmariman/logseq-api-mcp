"""Append markdown to a Logseq page on disk (file-mode graphs only).

Bypasses the HTTP API and appends ``content`` to the end of the page's
``.md`` file, creating the file if it does not exist. Unlike
``fs_write_page`` (which rewrites the whole file), this never reads the
existing content, so the read-modify-write conflict window shrinks to a
single append syscall — ideal for incremental journal edits.

Block separation: the file's final byte is inspected (O(1)); if it is not
a newline, a single ``\\n`` is inserted before ``content`` so the appended
text starts on its own line. The caller is responsible for passing valid
Logseq block markup (e.g. ``"- my note"``).

Concurrency note: like every ``fs_*`` tool, this writes the file behind
Logseq's back. If Logseq has the page open with unsaved changes it may
overwrite the append when it next persists. Prefer the API path
(``update_page``) when Logseq is actively editing the same page.
"""

import os
from pathlib import Path
from typing import List

from mcp.types import TextContent

from src.client.config import LogseqConfig
from src.client.logseq_client import LogseqClient
from src.fs.paths import resolve_page_path, target_path_for_write
from src.logging_setup import get_logger

_log = get_logger(__name__)


def _needs_leading_newline(target: Path) -> bool:
    """Return True if ``target`` exists, is non-empty, and lacks a trailing newline.

    Reads only the final byte so the cost is O(1) regardless of file size.
    Missing or empty files need no separator.
    """
    try:
        size = target.stat().st_size
    except FileNotFoundError:
        return False
    if size == 0:
        return False
    with open(target, "rb") as fh:
        fh.seek(-1, os.SEEK_END)
        return fh.read(1) != b"\n"


def _append(target: Path, content: str) -> None:
    """Append ``content`` to ``target``, creating parent dirs if needed.

    A single ``\\n`` separator is prepended when the existing file does not
    already end with a newline, so appended blocks never merge into the
    previous line.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    prefix = "\n" if _needs_leading_newline(target) else ""
    with open(target, "a", encoding="utf-8") as fh:
        fh.write(prefix + content)


async def _run(
    client: LogseqClient,
    config: LogseqConfig,
    page_name: str,
    content: str,
) -> List[TextContent]:
    """Append markdown to a page on disk, creating it if missing.

    Args:
        client: Unused; kept for the standard tool signature so the registry
            can inject the shared client uniformly.
        config: Provides ``graph_path`` and ``db_mode``.
        page_name: Page name as shown in Logseq.
        content: Markdown to append at the end of the file.

    Returns:
        Single :class:`TextContent` summarising the append (path, bytes
        added, effective action). On error, a ``❌``-prefixed message.

    Complexity: O(M) where M is len(content); the existing file is not read.
    """
    try:
        _log.debug("%s called: %r", __name__, page_name)

        if config.db_mode:
            return [
                TextContent(
                    type="text",
                    text="❌ fs_append is for file-mode graphs only "
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

        existing = resolve_page_path(config.graph_path, page_name)
        if existing is not None:
            target = existing
            action = "appended"
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

        _append(target, content)

        size = len(content.encode("utf-8"))
        rel = target.relative_to(Path(config.graph_path).resolve())
        return [
            TextContent(
                type="text",
                text=(
                    f"✅ {action.capitalize()} {page_name!r} (+{size} bytes)\n📁 {rel}"
                ),
            )
        ]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error appending to page: {exc}")]


async def fs_append(
    client: LogseqClient,
    config: LogseqConfig,
    page_name: str,
    content: str,
) -> List[TextContent]:
    """Append markdown to a Logseq page on disk, creating it if missing (file-mode only).

    Use this for low-conflict incremental edits — especially journals, which
    update_page cannot reach by their yyyy_MM_dd filename. The existing file
    is never read, so only the new content is written.

    Args:
        page_name: Page name as it appears in Logseq (e.g. "My Page",
            "Project/Sub"). Journal entries use Logseq's default filename
            format ``yyyy_MM_dd`` (e.g. "2026_05_27") and are created under
            journals/ automatically when missing.
        content: Markdown to append. Pass valid Logseq block markup
            (e.g. "- my note"); a newline separator is added automatically
            if the file does not already end with one.
    """
    # client/config are injected by the registry's adaptive binding.
    return await _run(client, config, page_name, content)
