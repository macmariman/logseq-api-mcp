"""Get the block tree structure of a Logseq page."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig
from src.tools.formatters.blocks import format_block_tree
from src.logging_setup import get_logger


_log = get_logger(__name__)


async def get_page_blocks(
    client: LogseqClient,
    config: LogseqConfig,
    page_identifier: str,
) -> List[TextContent]:
    """Get the tree structure of blocks that compose a page in Logseq.

    Returns a hierarchical view of all blocks formatted for LLM consumption.

    Args:
        client: LogseqClient instance (injected by the registry).
        config: LogseqConfig (reserved for future privacy filtering).
        page_identifier: The name or UUID of the page to get blocks from.

    Returns:
        List with one TextContent containing the formatted block tree.

    Complexity: O(N) where N is total block count.
    """
    try:
        _log.debug("%s called", __name__)
        blocks = await client.get_page_blocks_tree(page_identifier)
        if not blocks:
            return [
                TextContent(
                    type="text", text=f"✅ Page '{page_identifier}' has no blocks"
                )
            ]

        page_info = blocks[0].get("page", {}) if blocks else {}
        page_name = page_info.get("name", page_identifier)
        page_id = page_info.get("id", "N/A")

        lines = [
            "🌳 **PAGE BLOCKS TREE STRUCTURE**",
            f"📄 Page: {page_name} (ID: {page_id})",
            f"📊 Total blocks: {len(blocks)}",
            "",
            "🔗 **TREE HIERARCHY:**",
            "",
        ]
        for block in blocks:
            lines.extend(format_block_tree(block, level=0, max_level=8))
            lines.append("")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error fetching page blocks: {exc}")]
