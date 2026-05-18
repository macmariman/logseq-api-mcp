"""Get detailed content and metadata for a specific Logseq block."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import load_config
from src.tools.formatters.blocks import format_block_detail


async def _run(
    client: LogseqClient,
    block_uuid: str,
) -> List[TextContent]:
    """Fetch and format block details using an injected client.

    Args:
        client: LogseqClient instance.
        block_uuid: The UUID of the block to retrieve.

    Returns:
        List with one TextContent containing block details.

    Complexity: O(C) where C is child count (children fetched by Logseq).
    """
    try:
        block = await client.get_block(block_uuid, include_children=True)
        if not block:
            return [TextContent(type="text", text=f"❌ Block with UUID '{block_uuid}' not found")]

        lines = format_block_detail(block, is_child=False)
        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        return [TextContent(type="text", text=f"❌ Error fetching block content: {exc}")]


async def get_block_content(block_uuid: str) -> List[TextContent]:
    """Get detailed content and metadata for a specific block using its UUID.

    Returns comprehensive block information including properties, relationships,
    and content, formatted for optimal LLM consumption.

    Args:
        block_uuid: The UUID of the block to retrieve.

    Returns:
        List with one TextContent containing block details.

    Complexity: O(C) where C is child count.
    """
    return await _run(LogseqClient(load_config()), block_uuid)
