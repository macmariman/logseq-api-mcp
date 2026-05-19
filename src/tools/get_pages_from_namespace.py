"""Get all pages under a Logseq namespace."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig
from src.tools.formatters.pages import format_timestamp
from src.logging_setup import get_logger


_log = get_logger(__name__)


async def get_pages_from_namespace(
    client: LogseqClient,
    config: LogseqConfig,
    namespace: str,
) -> List[TextContent]:
    """Get all pages under a Logseq namespace hierarchy.

    Args:
        client: LogseqClient instance (injected by the registry).
        config: LogseqConfig (reserved for future use).
        namespace: The namespace prefix to list (e.g. "Project" returns "Project/Alpha", etc.).

    Returns:
        List with one TextContent containing the namespace page listing.

    Complexity: O(N) where N is page count.
    """
    try:
        _log.debug("%s called", __name__)
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
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [
            TextContent(type="text", text=f"❌ Error fetching namespace pages: {exc}")
        ]
