"""Search the Logseq graph for blocks, pages, and files."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig
from src.privacy.exclude_tags import filter_pages
from src.tools.formatters.search import (
    format_search_results_markdown_mode,
    format_search_results_db_mode,
)
from src.logging_setup import get_logger


_log = get_logger(__name__)


async def search(
    client: LogseqClient,
    config: LogseqConfig,
    query: str,
    limit: int = 20,
    include_blocks: bool = True,
    include_pages: bool = True,
    include_files: bool = False,
) -> List[TextContent]:
    """Search the Logseq graph for matching blocks, pages, and files.

    Args:
        client: LogseqClient instance (injected by the registry).
        config: LogseqConfig (provides db_mode and exclude_tags).
        query: Search string.
        limit: Maximum number of results per section (default 20).
        include_blocks: Whether to include block-content matches.
        include_pages: Whether to include page-name matches.
        include_files: Whether to include file-name matches.

    Returns:
        List with one TextContent containing formatted search results.

    Complexity: O(N) where N is total result count.
    """
    try:
        _log.debug("%s called", __name__)
        result = await client.search(query)

        excluded_page_names: frozenset[str] = frozenset()
        if config.exclude_tags:
            all_pages = await client.get_all_pages()
            visible = filter_pages(all_pages, config.exclude_tags)
            visible_names = {(p.get("name") or "").lower() for p in visible}
            all_names = {(p.get("name") or "").lower() for p in all_pages}
            excluded_page_names = frozenset(all_names - visible_names)

        if config.db_mode:
            text = format_search_results_db_mode(
                result,
                query,
                limit,
                include_blocks,
                include_pages,
                include_files,
                excluded_page_names,
            )
        else:
            text = format_search_results_markdown_mode(
                result,
                query,
                limit,
                include_blocks,
                include_pages,
                include_files,
                excluded_page_names,
            )

        return [TextContent(type="text", text=text)]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error searching Logseq: {exc}")]
