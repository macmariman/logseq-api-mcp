"""Get all pages from the Logseq graph."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig, load_config
from src.privacy.exclude_tags import filter_pages
from src.tools.formatters.pages import format_pages_listing


async def _run(
    client: LogseqClient,
    config: LogseqConfig,
    start: int | None = None,
    end: int | None = None,
    include_journals: bool = True,
) -> List[TextContent]:
    """Fetch and format all pages using an injected client and config.

    Args:
        client: LogseqClient instance.
        config: LogseqConfig (provides exclude_tags).
        start: Optional slice start index (0-based, inclusive).
        end: Optional slice end index (0-based, exclusive).
        include_journals: When False, journal/daily-note pages are hidden.

    Returns:
        List with one TextContent containing the formatted page listing.

    Complexity: O(N log N) where N is page count.
    """
    try:
        pages = await client.get_all_pages()

        # Apply tag-based exclusion first
        if config.exclude_tags:
            pages = filter_pages(pages, config.exclude_tags)

        # Apply journal filter
        if not include_journals:
            pages = [p for p in pages if not p.get("journal?", False)]

        text = format_pages_listing(pages, start, end)
        return [TextContent(type="text", text=text)]
    except Exception as exc:
        return [TextContent(type="text", text=f"❌ Error fetching pages: {exc}")]


async def get_all_pages(
    start: int | None = None,
    end: int | None = None,
    include_journals: bool = True,
) -> List[TextContent]:
    """Get a listing of all pages in the Logseq graph with essential metadata.

    Returns a clean listing with journal and regular page sections, optimized
    for LLM consumption. Pages tagged with LOGSEQ_EXCLUDE_TAGS are hidden.

    Args:
        start: Starting index (0-based, inclusive). None = beginning.
        end: Ending index (0-based, exclusive). None = all pages.
        include_journals: When False, journal/daily-note pages are omitted.

    Returns:
        List with one TextContent containing the formatted page listing.

    Complexity: O(N log N) where N is page count.
    """
    cfg = load_config()
    return await _run(LogseqClient(cfg), cfg, start, end, include_journals)
