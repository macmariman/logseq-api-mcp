"""Create a new page in Logseq."""

from typing import Any, Dict, List, Optional
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import load_config


async def _run(
    client: LogseqClient,
    page_name: str,
    properties: Optional[Dict[str, Any]] = None,
    fmt: Optional[str] = None,
) -> List[TextContent]:
    """Create a page using an injected client.

    Args:
        client: LogseqClient instance.
        page_name: The name of the page to create.
        properties: Optional page-level properties dict.
        fmt: Optional format string ('markdown' or 'org').

    Returns:
        List with one TextContent describing the result.

    Complexity: O(1).
    """
    try:
        result = await client.create_page(page_name, properties=properties, fmt=fmt)

        if not result:
            return [TextContent(type="text", text="❌ Failed to create page: No response from Logseq API")]

        lines = ["✅ **PAGE CREATED SUCCESSFULLY**", f"📄 Page Name: {page_name}", ""]

        if isinstance(result, dict):
            page_id = result.get("id", "N/A")
            page_uuid = result.get("uuid", "N/A")
            original_name = result.get("originalName", page_name)
            is_journal = result.get("journal?", False)
            page_format = result.get("format", "markdown")

            lines.extend([
                "📊 **PAGE DETAILS:**",
                f"• ID: {page_id}",
                f"• UUID: {page_uuid}",
                f"• Original Name: {original_name}",
                f"• Format: {page_format}",
                f"• Journal Page: {'Yes' if is_journal else 'No'}",
                "",
            ])

            page_properties = result.get("properties", {})
            if page_properties:
                lines.extend([
                    "⚙️ **PAGE PROPERTIES:**",
                    *[f"• {k}: {v}" for k, v in page_properties.items()],
                    "",
                ])

        if properties:
            lines.append(f"⚙️ Properties set: {len(properties)} items")
        if fmt:
            lines.append(f"📝 Format: {fmt}")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        return [TextContent(type="text", text=f"❌ Error creating page: {exc}")]


async def create_page(
    page_name: str,
    properties: Optional[Dict[str, Any]] = None,
    format: Optional[str] = None,
) -> List[TextContent]:
    """Create a new page in Logseq.

    Args:
        page_name: The name of the page to create.
        properties: Optional dictionary of properties to set on the page.
        format: Optional format for the page ('markdown' or 'org').

    Returns:
        List with one TextContent describing success or failure.

    Complexity: O(1).
    """
    return await _run(LogseqClient(load_config()), page_name, properties, format)
