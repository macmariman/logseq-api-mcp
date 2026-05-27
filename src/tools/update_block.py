"""Update the content of a Logseq block."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig
from src.logging_setup import get_logger
from src.tools._marker import hidden


_log = get_logger(__name__)


# Hidden: surgical UUID-preserving edit; rarely needed for personal file-mode graphs.
@hidden
async def update_block(
    client: LogseqClient,
    config: LogseqConfig,
    block_uuid: str,
    content: str,
) -> List[TextContent]:
    """Update the content of a Logseq block.

    Args:
        client: LogseqClient instance.
        config: LogseqConfig (reserved for future use).
        block_uuid: UUID of the block to update.
        content: New content string to set on the block.

    Returns:
        List with one TextContent describing success or failure.

    Complexity: O(1).
    """
    try:
        _log.debug("%s called", __name__)
        if not content or not content.strip():
            return [TextContent(type="text", text="❌ Content must not be empty")]

        block = await client.get_block(block_uuid, include_children=False)
        if not block:
            return [TextContent(type="text", text=f"❌ Block '{block_uuid}' not found")]

        await client.update_block(block_uuid, content)
        return [
            TextContent(
                type="text",
                text=f"✅ Block '{block_uuid}' updated successfully\n📝 New content: {content[:120]}",
            )
        ]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error updating block: {exc}")]
