"""Edit a block in Logseq."""

from typing import Any, Dict, List, Optional
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig
from src.logging_setup import get_logger
from src.tools._marker import hidden


_log = get_logger(__name__)


# Hidden: surgical UUID-preserving edit; rarely needed for personal file-mode graphs.
@hidden
async def edit_block(
    client: LogseqClient,
    config: LogseqConfig,
    block_identity: str,
    content: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
    cursor_position: Optional[int] = None,
    focus: Optional[bool] = None,
) -> List[TextContent]:
    """Edit a block in Logseq.

    Args:
        client: LogseqClient instance.
        config: LogseqConfig (reserved for future use).
        block_identity: The UUID of the block to edit (BlockIdentity).
        content: Optional new content for the block.
        properties: Optional dictionary of properties to update on the block.
        cursor_position: Optional cursor position for editing (0-based index).
        focus: Optional boolean to focus the block after editing.

    Returns:
        List with one TextContent describing success or failure.

    Complexity: O(1).
    """
    try:
        _log.debug("%s called", __name__)
        result = await client.edit_block(
            block_identity,
            content=content,
            properties=properties,
            cursor_pos=cursor_position,
            focus=focus,
        )

        if not result and result != {}:
            return [
                TextContent(
                    type="text",
                    text="❌ Failed to edit block: No response from Logseq API",
                )
            ]

        lines = [
            "✅ **BLOCK EDITED SUCCESSFULLY**",
            f"🔗 Block UUID: {block_identity}",
            "",
        ]

        edit_details = []
        if content is not None:
            edit_details.append("📝 Content updated")
        if properties is not None:
            edit_details.append(f"⚙️ Properties updated ({len(properties)} items)")
        if cursor_position is not None:
            edit_details.append(f"📍 Cursor positioned at index {cursor_position}")
        if focus is not None:
            edit_details.append(f"🎯 Focus: {'Enabled' if focus else 'Disabled'}")

        if edit_details:
            lines.extend(
                ["📊 **EDIT DETAILS:**", *[f"• {d}" for d in edit_details], ""]
            )

        if content is not None:
            preview = content[:100] + "..." if len(content) > 100 else content
            lines.extend(["📝 **UPDATED CONTENT:**", "```", preview, "```", ""])

        if properties is not None:
            lines.extend(
                [
                    "⚙️ **UPDATED PROPERTIES:**",
                    *[f"• {k}: {v}" for k, v in properties.items()],
                    "",
                ]
            )

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error editing block: {exc}")]
