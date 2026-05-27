"""Get detailed content and metadata for a specific Logseq block."""

import json
from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig
from src.tools.formatters.blocks import format_block_detail
from src.logging_setup import get_logger
from src.tools._marker import hidden


_log = get_logger(__name__)


# Hidden: surgical UUID-targeted read; rarely needed when reading full pages via fs_read_page.
@hidden
async def get_block_content(
    client: LogseqClient,
    config: LogseqConfig,
    block_uuid: str,
    fmt: str = "text",
    include_children: bool = True,
) -> List[TextContent]:
    """Get detailed content and metadata for a specific block using its UUID.

    Returns comprehensive block information including properties, relationships,
    and content, formatted for optimal LLM consumption.

    Args:
        client: LogseqClient instance (injected by the registry).
        config: LogseqConfig (provides db_mode flag).
        block_uuid: The UUID of the block to retrieve.
        fmt: Output format — "text" (default) or "json".
        include_children: When False, child blocks are excluded from the result.

    Returns:
        List with one TextContent containing block details.

    Complexity: O(C) where C is child count.
    """
    try:
        _log.debug("%s called", __name__)
        block = await client.get_block(block_uuid, include_children=include_children)
        if not block:
            return [
                TextContent(
                    type="text", text=f"❌ Block with UUID '{block_uuid}' not found"
                )
            ]

        db_props: dict[str, dict] = {}
        if config.db_mode:
            db_props = await client.get_blocks_db_properties([block])

        if fmt == "json":
            payload: dict = {
                "uuid": block.get("uuid"),
                "content": block.get("content", ""),
                "properties": block.get("properties", {}),
                "level": block.get("level", 0),
                "page": block.get("page", {}),
            }
            if db_props:
                payload["db_properties"] = db_props.get(block_uuid, {})
            if include_children:
                payload["children"] = block.get("children", [])
            return [
                TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))
            ]

        lines = format_block_detail(block, is_child=False)

        if db_props:
            extra = db_props.get(block_uuid, {})
            if extra:
                lines.append("   DB Properties:")
                for k, v in extra.items():
                    lines.append(f"     {k}:: {v}")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [
            TextContent(type="text", text=f"❌ Error fetching block content: {exc}")
        ]
