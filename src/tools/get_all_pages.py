"""Get all pages from the Logseq graph."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import load_config
from src.tools.formatters.pages import format_pages_listing


async def _run(
    client: LogseqClient,
    start: int | None = None,
    end: int | None = None,
) -> List[TextContent]:
    """Fetch and format all pages using an injected client.

    Args:
        client: LogseqClient instance.
        start: Optional slice start index (0-based, inclusive).
        end: Optional slice end index (0-based, exclusive).

    Returns:
        List with one TextContent containing the formatted page listing.

    Complexity: O(N log N) where N is page count.
    """
    try:
        pages = await client.get_all_pages()
        text = format_pages_listing(pages, start, end)
        return [TextContent(type="text", text=text)]
    except Exception as exc:
        return [TextContent(type="text", text=f"❌ Error fetching pages: {exc}")]


async def get_all_pages(
    start: int | None = None, end: int | None = None
) -> List[TextContent]:
    """Get a simple list of all pages in the Logseq graph with essential metadata.

    Returns a clean listing with journal and regular page sections, optimized
    for LLM consumption. Can be sliced with start and end parameters.

    Args:
        start: Starting index (0-based, inclusive). None = beginning.
        end: Ending index (0-based, exclusive). None = all pages.

    Returns:
        List with one TextContent containing the formatted page listing.

    Complexity: O(N log N) where N is page count.
    """
    return await _run(LogseqClient(load_config()), start, end)
