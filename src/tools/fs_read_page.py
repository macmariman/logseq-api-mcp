"""Read a Logseq page directly from disk (file-mode graphs only).

Bypasses the HTTP API and returns the raw markdown content of the page's
``.md`` file. Use this for fast, lossless reads when working on a
file-mode graph; the API path (parsed block tree) is still available for
DB-mode graphs.
"""

from pathlib import Path
from typing import List

from mcp.types import TextContent

from src.client.config import LogseqConfig
from src.client.logseq_client import LogseqClient
from src.fs.paths import resolve_page_path
from src.logging_setup import get_logger

_log = get_logger(__name__)


async def _run(
    client: LogseqClient,
    config: LogseqConfig,
    page_name: str,
) -> List[TextContent]:
    """Read a page from disk and return its raw markdown.

    Args:
        client: Unused; kept for the standard tool signature so the registry
            can inject the shared client uniformly.
        config: Provides ``graph_path`` and ``db_mode``.
        page_name: Page name as shown in Logseq.

    Returns:
        List with one :class:`TextContent` containing a small header
        (page name, relative path, size, line count) followed by the raw
        file contents. On error, a single ``❌``-prefixed message.

    Complexity: O(F) where F is the file size in bytes.
    """
    try:
        _log.debug("%s called: %r", __name__, page_name)

        if config.db_mode:
            return [
                TextContent(
                    type="text",
                    text="❌ fs_read_page is for file-mode graphs only "
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

        path = resolve_page_path(config.graph_path, page_name)
        if path is None:
            return [
                TextContent(
                    type="text",
                    text=(
                        f"❌ Page not found: {page_name!r} "
                        "(searched pages/ and journals/)."
                    ),
                )
            ]

        content = path.read_text(encoding="utf-8")
        size = len(content.encode("utf-8"))
        lines = len(content.splitlines())
        # Resolve graph_path so relative_to works when the user-provided path
        # contains symlinked segments (e.g. /tmp → /private/tmp on macOS).
        rel = path.relative_to(Path(config.graph_path).resolve())

        header = f"📄 {page_name}\n📁 {rel}\n📏 {size} bytes, {lines} lines\n\n---\n\n"
        return [TextContent(type="text", text=header + content)]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error reading page: {exc}")]


async def fs_read_page(
    client: LogseqClient,
    config: LogseqConfig,
    page_name: str,
) -> List[TextContent]:
    """Read a Logseq page directly from disk. Returns raw markdown exactly as stored.

    Args:
        page_name: Page name as it appears in Logseq (e.g. "My Page", "Project/Sub").
    """
    # client/config are injected by the registry's adaptive binding.
    return await _run(client, config, page_name)
