"""Get all pages under a Logseq namespace."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig, load_config
from src.tools.formatters.pages import format_timestamp


async def _run(
    client: LogseqClient,
    config: LogseqConfig,
    namespace: str,
) -> List[TextContent]:
    """Fetch pages in a namespace using an injected client.

    Args:
        client: LogseqClient instance.
        config: LogseqConfig (reserved for future use).
        namespace: The namespace prefix to list (e.g. "Project").

    Returns:
        List with one TextContent containing the namespace page listing.

    Complexity: O(N) where N is page count.
    """
    try:
        pages = await client.get_pages_from_namespace(namespace)

        lines = [
            "📂 **NAMESPACE PAGES**",
            f"🗂️ Namespace: {namespace}",
            f"📊 Pages found: {len(pages)}",
            "",
        ]

        if not pages:
            lines.append(f"*(No pages found under namespace '{namespace}')*")
        else:
            for page in pages:
                name = page.get("originalName") or page.get("name", "?")
                uuid = page.get("uuid", "N/A")
                updated = format_timestamp(page.get("updatedAt"))
                lines.append(f"• 📄 **{name}**")
                lines.append(f"  🔑 UUID: {uuid} | 🔄 Updated: {updated}")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        return [TextContent(type="text", text=f"❌ Error fetching namespace pages: {exc}")]


async def get_pages_from_namespace(namespace: str) -> List[TextContent]:
    """Get all pages under a Logseq namespace hierarchy.

    Args:
        namespace: The namespace prefix to list (e.g. "Project" returns "Project/Alpha", etc.).

    Returns:
        List with one TextContent containing the namespace page listing.

    Complexity: O(N) where N is page count.
    """
    cfg = load_config()
    return await _run(LogseqClient(cfg), cfg, namespace)
