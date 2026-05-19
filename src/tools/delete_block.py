"""Delete a block from Logseq."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig
from src.logging_setup import get_logger


_log = get_logger(__name__)


async def delete_block(
    client: LogseqClient,
    config: LogseqConfig,
    block_uuid: str,
) -> List[TextContent]:
    """Delete a block from Logseq by its UUID.

    Args:
        client: LogseqClient instance.
        config: LogseqConfig (reserved for future use).
        block_uuid: UUID of the block to delete.

    Returns:
        List with one TextContent describing success or failure.

    Complexity: O(1).
    """
    try:
        _log.debug("%s called", __name__)
        block = await client.get_block(block_uuid, include_children=False)
        if not block:
            return [TextContent(type="text", text=f"❌ Block '{block_uuid}' not found")]

        await client.delete_block(block_uuid)
        return [
            TextContent(
                type="text", text=f"✅ Block '{block_uuid}' deleted successfully"
            )
        ]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error deleting block: {exc}")]
