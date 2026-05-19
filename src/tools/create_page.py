"""Create a new page in Logseq."""

from typing import Any, Dict, List, Optional
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig
from src.parser.markdown import parse_content
from src.logging_setup import get_logger


_log = get_logger(__name__)


async def create_page(
    client: LogseqClient,
    config: LogseqConfig,
    page_name: str,
    properties: Optional[Dict[str, Any]] = None,
    fmt: Optional[str] = None,
    content: Optional[str] = None,
) -> List[TextContent]:
    """Create a new page in Logseq with optional markdown content.

    Args:
        client: LogseqClient instance (injected by the registry).
        config: LogseqConfig (reserved for future use).
        page_name: The name of the page to create.
        properties: Optional dictionary of properties to set on the page.
        fmt: Optional format for the page ('markdown' or 'org').
        content: Optional markdown content; parsed into blocks and inserted.

    Returns:
        List with one TextContent describing success or failure.

    Complexity: O(B) where B is parsed block count.
    """
    try:
        _log.debug("%s called", __name__)
        merged_props = dict(properties or {})
        batch_blocks: list[dict] = []

        if content and content.strip():
            parsed = parse_content(content)
            if parsed.properties:
                merged_props = {**parsed.properties, **merged_props}
            batch_blocks = parsed.to_batch_format()

        result = await client.create_page(
            page_name,
            properties=merged_props or None,
            fmt=fmt,
        )

        if not result:
            return [
                TextContent(
                    type="text",
                    text="❌ Failed to create page: No response from Logseq API",
                )
            ]

        lines = ["✅ **PAGE CREATED SUCCESSFULLY**", f"📄 Page Name: {page_name}", ""]

        if isinstance(result, dict):
            page_id = result.get("id", "N/A")
            page_uuid = result.get("uuid", "N/A")
            original_name = result.get("originalName", page_name)
            is_journal = result.get("journal?", False)
            page_format = result.get("format", "markdown")

            lines.extend(
                [
                    "📊 **PAGE DETAILS:**",
                    f"• ID: {page_id}",
                    f"• UUID: {page_uuid}",
                    f"• Original Name: {original_name}",
                    f"• Format: {page_format}",
                    f"• Journal Page: {'Yes' if is_journal else 'No'}",
                    "",
                ]
            )

            page_properties = result.get("properties", {})
            if page_properties:
                lines.extend(
                    [
                        "⚙️ **PAGE PROPERTIES:**",
                        *[f"• {k}: {v}" for k, v in page_properties.items()],
                        "",
                    ]
                )

        if merged_props:
            lines.append(f"⚙️ Properties set: {len(merged_props)} items")
        if fmt:
            lines.append(f"📝 Format: {fmt}")

        if batch_blocks:
            page_uuid = result.get("uuid") if isinstance(result, dict) else None
            if page_uuid:
                await client.insert_batch_block(page_uuid, batch_blocks, sibling=False)
            lines.append(f"📝 Content blocks inserted: {len(batch_blocks)}")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error creating page: {exc}")]
