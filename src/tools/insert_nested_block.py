"""Insert a child or sibling block into Logseq."""

from typing import Any, Dict, List, Optional
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig, load_config
from src.logging_setup import get_logger



_log = get_logger(__name__)

async def _run(
    client: LogseqClient,
    config: LogseqConfig,
    parent_block_uuid: str,
    content: str,
    properties: Optional[Dict[str, Any]] = None,
    sibling: bool = False,
) -> List[TextContent]:
    """Insert a block relative to a parent using an injected client.

    Args:
        client: LogseqClient instance.
        config: LogseqConfig (reserved for future use).
        parent_block_uuid: UUID of the parent (or reference) block.
        content: Content string for the new block.
        properties: Optional properties dict for the new block.
        sibling: When True, insert as a sibling; when False (default), insert as a child.

    Returns:
        List with one TextContent describing the result.

    Complexity: O(1).
    """
    try:
        _log.debug("%s called", __name__)
        if not content or not content.strip():
            return [TextContent(type="text", text="❌ Content must not be empty")]

        parent = await client.get_block(parent_block_uuid, include_children=False)
        if not parent:
            return [TextContent(type="text", text=f"❌ Parent block '{parent_block_uuid}' not found")]

        new_block = await client.insert_block(
            parent_block_uuid,
            content,
            properties=properties,
            sibling=sibling,
        )

        new_uuid = (new_block or {}).get("uuid", "unknown")
        position = "sibling" if sibling else "child"
        lines = [
            f"✅ Block inserted as {position} of '{parent_block_uuid}'",
            f"🔑 New block UUID: {new_uuid}",
            f"📝 Content: {content[:120]}",
        ]
        if properties:
            lines.append(f"⚙️ Properties: {len(properties)} set")
        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error inserting block: {exc}")]


async def insert_nested_block(
    parent_block_uuid: str,
    content: str,
    properties: Optional[Dict[str, Any]] = None,
    sibling: bool = False,
) -> List[TextContent]:
    """Insert a new block as a child or sibling of an existing block.

    Args:
        parent_block_uuid: UUID of the reference block.
        content: Content string for the new block.
        properties: Optional properties dict for the new block.
        sibling: When True, insert as a sibling; when False (default), insert as a child.

    Returns:
        List with one TextContent describing success or failure.

    Complexity: O(1).
    """
    cfg = load_config()
    return await _run(LogseqClient(cfg), cfg, parent_block_uuid, content, properties, sibling)
