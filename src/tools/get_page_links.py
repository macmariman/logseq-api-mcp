"""Backward-compatible alias for get_page_backlinks."""

from typing import List
from mcp.types import TextContent

from src.tools.get_page_backlinks import _run, get_page_backlinks


async def get_page_links(
    page_identifier: str,
    include_content: bool = True,
) -> List[TextContent]:
    """Get pages that link to the specified page (alias for get_page_backlinks).

    Args:
        page_identifier: The name or UUID of the page to find backlinks for.
        include_content: When True, include the text of each referencing block.

    Returns:
        List with one TextContent containing the backlink analysis.

    Complexity: O(P + R) where P is page count, R is reference count.
    """
    return await get_page_backlinks(page_identifier, include_content)


__all__ = ["_run", "get_page_links"]
