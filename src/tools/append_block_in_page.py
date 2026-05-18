"""Append a new block to a Logseq page."""

from typing import Optional, List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import load_config


async def _run(
    client: LogseqClient,
    page_identifier: str,
    content: str,
    before: Optional[str] = None,
    sibling: Optional[str] = None,
    is_page_block: Optional[bool] = None,
) -> List[TextContent]:
    """Append a block to a page using an injected client.

    Args:
        client: LogseqClient instance.
        page_identifier: The name or UUID of the target page.
        content: Block text content.
        before: Optional UUID of a block to insert before.
        sibling: Optional UUID of a sibling block for positioning.
        is_page_block: Optional flag to mark as page-level block.

    Returns:
        List with one TextContent describing the result.

    Raises:
        Nothing — errors are caught and returned as TextContent.

    Complexity: O(1).
    """
    try:
        options: dict = {}
        if before is not None:
            options["before"] = before
        if sibling is not None:
            options["sibling"] = sibling
        if is_page_block is not None:
            options["isPageBlock"] = is_page_block

        result = await client.append_block_in_page(page_identifier, content, options or None)

        if not result:
            return [TextContent(type="text", text="❌ Failed to append block: No response from Logseq API")]

        lines = [
            "✅ **BLOCK APPENDED SUCCESSFULLY**",
            f"📄 Page: {page_identifier}",
            f"📝 Content: {content}",
            "",
        ]
        if before:
            lines.append(f"📍 Positioned before block: {before}")
        if sibling:
            lines.append(f"📍 Positioned as sibling of: {sibling}")
        if is_page_block:
            lines.append("📍 Block type: Page-level block")
        if not (before or sibling or is_page_block):
            lines.append("📍 Positioned: At the end of the page")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        return [TextContent(type="text", text=f"❌ Error appending block: {exc}")]


async def append_block_in_page(
    page_identifier: str,
    content: str,
    before: Optional[str] = None,
    sibling: Optional[str] = None,
    is_page_block: Optional[bool] = None,
) -> List[TextContent]:
    """Append a new block to a specified page in Logseq.

    Args:
        page_identifier: The name or UUID of the page to append the block to.
        content: The content of the block to append.
        before: Optional UUID of a block to insert before.
        sibling: Optional UUID of a sibling block for positioning.
        is_page_block: Optional boolean to indicate if this is a page-level block.

    Returns:
        List with one TextContent describing success or failure.

    Complexity: O(1).
    """
    return await _run(
        LogseqClient(load_config()),
        page_identifier,
        content,
        before,
        sibling,
        is_page_block,
    )
