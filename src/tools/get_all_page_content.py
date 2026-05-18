"""Get comprehensive content of a Logseq page."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import load_config
from src.tools.formatters.blocks import format_block_tree


def _format_content_preview(content: str, max_length: int = 300) -> str:
    """Strip metadata lines and return a clean content preview.

    Args:
        content: Raw block content string.
        max_length: Maximum character length.

    Returns:
        Cleaned, possibly-truncated preview string.

    Complexity: O(L) where L is line count.
    """
    lines = [
        line.strip()
        for line in content.strip().split("\n")
        if line.strip()
        and not line.strip().startswith("::")
        and "card-" not in line
        and "collapsed::" not in line
    ]
    preview = " ".join(lines).replace("[[", "").replace("]]", "").replace("#card", "").strip()
    return preview[:max_length] + "..." if len(preview) > max_length else preview


async def _run(
    client: LogseqClient,
    page_identifier: str,
) -> List[TextContent]:
    """Fetch and format full page content using an injected client.

    Args:
        client: LogseqClient instance.
        page_identifier: The name or UUID of the page to get content from.

    Returns:
        List with one TextContent containing the full page content.

    Complexity: O(N) where N is total block count.
    """
    try:
        # Fetch page metadata and blocks concurrently where possible
        page = await client.get_page(page_identifier)
        blocks = await client.get_page_blocks_tree(page_identifier)

        if not page and not blocks:
            return [TextContent(type="text", text=f"❌ Page '{page_identifier}' not found")]

        page_name = (page or {}).get("originalName") or (page or {}).get("name", page_identifier)
        page_id = (page or {}).get("id", "N/A")
        page_uuid = (page or {}).get("uuid", "N/A")

        lines = [
            "📖 **PAGE CONTENT**",
            f"📄 Page: {page_name}",
            f"🔑 ID: {page_id} | UUID: {page_uuid}",
            f"📊 Blocks: {len(blocks)}",
            "",
            "**CONTENT:**",
            "",
        ]

        if not blocks:
            lines.append("[No content]")
        else:
            for block in blocks:
                lines.extend(format_block_tree(block, level=0, max_level=8))

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        return [TextContent(type="text", text=f"❌ Error fetching page content: {exc}")]


async def get_all_page_content(page_identifier: str) -> List[TextContent]:
    """Get comprehensive page content including all blocks and their full content.

    Args:
        page_identifier: The name or UUID of the page to get complete content from.

    Returns:
        List with one TextContent containing the full page content.

    Complexity: O(N) where N is total block count.
    """
    return await _run(LogseqClient(load_config()), page_identifier)
