"""Set properties on a Logseq block (DB-mode only)."""

from typing import Any, Dict, List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig, load_config


async def _run(
    client: LogseqClient,
    config: LogseqConfig,
    block_uuid: str,
    properties: Dict[str, Any],
) -> List[TextContent]:
    """Set properties on a block via upsertBlockProperty (DB-mode only).

    Args:
        client: LogseqClient instance.
        config: LogseqConfig — db_mode must be True.
        block_uuid: UUID of the block to update.
        properties: Dict of property key → value pairs to set.

    Returns:
        List with one TextContent describing the result.

    Complexity: O(P) where P is property count.
    """
    try:
        if not config.db_mode:
            return [TextContent(
                type="text",
                text="❌ set_block_properties requires DB mode (LOGSEQ_DB_MODE=true)"
            )]

        if not properties:
            return [TextContent(type="text", text="❌ Properties dict must not be empty")]

        block = await client.get_block(block_uuid, include_children=False)
        if not block:
            return [TextContent(type="text", text=f"❌ Block '{block_uuid}' not found")]

        for key, value in properties.items():
            await client.upsert_block_property(block_uuid, key, value)

        lines = [
            f"✅ Properties set on block '{block_uuid}'",
            f"⚙️ {len(properties)} propert{'ies' if len(properties) != 1 else 'y'} updated:",
            *[f"  • {k}:: {v}" for k, v in properties.items()],
        ]
        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        return [TextContent(type="text", text=f"❌ Error setting block properties: {exc}")]


async def set_block_properties(
    block_uuid: str,
    properties: Dict[str, Any],
) -> List[TextContent]:
    """Set one or more properties on a Logseq block (DB-mode only).

    Args:
        block_uuid: UUID of the block to update.
        properties: Dict of property key → value pairs to set.

    Returns:
        List with one TextContent describing success or failure.

    Complexity: O(P) where P is property count.
    """
    cfg = load_config()
    return await _run(LogseqClient(cfg), cfg, block_uuid, properties)
