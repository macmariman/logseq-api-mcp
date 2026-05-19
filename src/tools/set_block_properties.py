"""Set properties on a Logseq block (DB-mode only)."""

from typing import Any, Dict, List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig
from src.logging_setup import get_logger


_log = get_logger(__name__)


async def set_block_properties(
    client: LogseqClient,
    config: LogseqConfig,
    block_uuid: str,
    properties: Dict[str, Any],
) -> List[TextContent]:
    """Set one or more properties on a Logseq block (DB-mode only).

    Args:
        client: LogseqClient instance.
        config: LogseqConfig — db_mode must be True.
        block_uuid: UUID of the block to update.
        properties: Dict of property key → value pairs to set.

    Returns:
        List with one TextContent describing success or failure.

    Complexity: O(P) where P is property count.
    """
    try:
        _log.debug("%s called", __name__)
        if not config.db_mode:
            return [
                TextContent(
                    type="text",
                    text="❌ set_block_properties requires DB mode (LOGSEQ_DB_MODE=true)",
                )
            ]

        if not properties:
            return [
                TextContent(type="text", text="❌ Properties dict must not be empty")
            ]

        block = await client.get_block(block_uuid, include_children=False)
        if not block:
            return [TextContent(type="text", text=f"❌ Block '{block_uuid}' not found")]

        for key, value in properties.items():
            ident = await client.resolve_property_ident(key)
            resolved_key = ident if ident is not None else key
            await client.upsert_block_property(block_uuid, resolved_key, value)

        lines = [
            f"✅ Properties set on block '{block_uuid}'",
            f"⚙️ {len(properties)} propert{'ies' if len(properties) != 1 else 'y'} updated:",
            *[f"  • {k}:: {v}" for k, v in properties.items()],
        ]
        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [
            TextContent(type="text", text=f"❌ Error setting block properties: {exc}")
        ]
