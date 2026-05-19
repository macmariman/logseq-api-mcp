"""Delete a page from Logseq."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig, load_config
from src.logging_setup import get_logger



_log = get_logger(__name__)

async def _run(
    client: LogseqClient,
    config: LogseqConfig,
    page_name: str,
) -> List[TextContent]:
    """Delete a page using an injected client.

    Args:
        client: LogseqClient instance.
        config: LogseqConfig (reserved for future privacy guard).
        page_name: Name of the page to delete.

    Returns:
        List with one TextContent describing the result.

    Complexity: O(1).
    """
    try:
        _log.debug("%s called", __name__)
        page = await client.get_page(page_name)
        if not page:
            return [TextContent(type="text", text=f"❌ Page '{page_name}' not found")]

        await client.delete_page(page_name)
        return [TextContent(type="text", text=f"✅ Page '{page_name}' deleted successfully")]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error deleting page: {exc}")]


async def delete_page(page_name: str) -> List[TextContent]:
    """Delete a page from the Logseq graph.

    Args:
        page_name: Name of the page to delete.

    Returns:
        List with one TextContent describing success or failure.

    Complexity: O(1).
    """
    cfg = load_config()
    return await _run(LogseqClient(cfg), cfg, page_name)
