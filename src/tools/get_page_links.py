"""Backward-compatible alias for get_page_backlinks."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig
from src.tools.get_page_backlinks import get_page_backlinks


async def get_page_links(
    client: LogseqClient,
    config: LogseqConfig,
    page_identifier: str,
    include_content: bool = True,
) -> List[TextContent]:
    """Get pages that link to the specified page (alias for get_page_backlinks).

    Args:
        client: LogseqClient instance (injected by the registry).
        config: LogseqConfig (provides exclude_tags for privacy filtering).
        page_identifier: The name or UUID of the page to find backlinks for.
        include_content: When True, include the text of each referencing block.

    Returns:
        List with one TextContent containing the backlink analysis.

    Complexity: O(P + R) where P is page count, R is reference count.
    """
    return await get_page_backlinks(client, config, page_identifier, include_content)


__all__ = ["get_page_links"]
