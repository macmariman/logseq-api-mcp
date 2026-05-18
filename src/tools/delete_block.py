"""Delete a block from Logseq."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig, load_config


async def _run(
    client: LogseqClient,
    config: LogseqConfig,
    block_uuid: str,
) -> List[TextContent]:
    """Delete a block using an injected client.

    Args:
        client: LogseqClient instance.
        config: LogseqConfig (reserved for future use).
        block_uuid: UUID of the block to delete.

    Returns:
        List with one TextContent describing the result.

    Complexity: O(1).
    """
    try:
        block = await client.get_block(block_uuid, include_children=False)
        if not block:
            return [TextContent(type="text", text=f"❌ Block '{block_uuid}' not found")]

        await client.delete_block(block_uuid)
        return [TextContent(type="text", text=f"✅ Block '{block_uuid}' deleted successfully")]

    except Exception as exc:
        return [TextContent(type="text", text=f"❌ Error deleting block: {exc}")]


async def delete_block(block_uuid: str) -> List[TextContent]:
    """Delete a block from Logseq by its UUID.

    Args:
        block_uuid: UUID of the block to delete.

    Returns:
        List with one TextContent describing success or failure.

    Complexity: O(1).
    """
    cfg = load_config()
    return await _run(LogseqClient(cfg), cfg, block_uuid)
