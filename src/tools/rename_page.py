"""Rename a page in Logseq."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig, load_config
from src.logging_setup import get_logger



_log = get_logger(__name__)

async def _run(
    client: LogseqClient,
    config: LogseqConfig,
    old_name: str,
    new_name: str,
) -> List[TextContent]:
    """Rename a page using an injected client.

    Args:
        client: LogseqClient instance.
        config: LogseqConfig (reserved for future use).
        old_name: Current page name.
        new_name: Desired new page name.

    Returns:
        List with one TextContent describing the result.

    Complexity: O(1).
    """
    try:
        _log.debug("%s called", __name__)
        if not new_name or not new_name.strip():
            return [TextContent(type="text", text="❌ New name must not be empty")]

        if old_name == new_name:
            return [TextContent(type="text", text=f"❌ New name is identical to current name '{old_name}'")]

        page = await client.get_page(old_name)
        if not page:
            return [TextContent(type="text", text=f"❌ Page '{old_name}' not found")]

        await client.rename_page(old_name, new_name)
        return [TextContent(
            type="text",
            text=f"✅ Page renamed: '{old_name}' → '{new_name}'"
        )]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error renaming page: {exc}")]


async def rename_page(old_name: str, new_name: str) -> List[TextContent]:
    """Rename a page in Logseq.

    Args:
        old_name: Current name of the page.
        new_name: New name to assign to the page.

    Returns:
        List with one TextContent describing success or failure.

    Complexity: O(1).
    """
    cfg = load_config()
    return await _run(LogseqClient(cfg), cfg, old_name, new_name)
