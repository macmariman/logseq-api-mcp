"""Delete a page from Logseq."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig
from src.logging_setup import get_logger


_log = get_logger(__name__)


async def delete_page(
    client: LogseqClient,
    config: LogseqConfig,
    page_name: str,
) -> List[TextContent]:
    """Delete a page from the Logseq graph.

    Args:
        client: LogseqClient instance (injected by the registry).
        config: LogseqConfig (reserved for future privacy guard).
        page_name: Name of the page to delete.

    Returns:
        List with one TextContent describing success or failure.

    Complexity: O(1).
    """
    try:
        _log.debug("%s called", __name__)
        page = await client.get_page(page_name)
        if not page:
            return [TextContent(type="text", text=f"❌ Page '{page_name}' not found")]

        await client.delete_page(page_name)
        return [
            TextContent(type="text", text=f"✅ Page '{page_name}' deleted successfully")
        ]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error deleting page: {exc}")]
