"""Find Logseq pages that have a specific property (and optionally a specific value)."""

import re
from typing import List, Optional
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig, load_config
from src.privacy.exclude_tags import filter_pages

_VALID_PROP_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")


async def _run(
    client: LogseqClient,
    config: LogseqConfig,
    property_name: str,
    property_value: Optional[str] = None,
    limit: int = 100,
) -> List[TextContent]:
    """Find pages by property using an injected client.

    Args:
        client: LogseqClient instance.
        config: LogseqConfig (reserved for future use).
        property_name: Property key to search for (alphanumeric/dash/underscore only).
        property_value: Optional exact value to match.
        limit: Maximum number of results to return.

    Returns:
        List with one TextContent containing matching pages.

    Complexity: O(N) where N is result count.
    """
    try:
        if not _VALID_PROP_RE.match(property_name):
            return [TextContent(
                type="text",
                text=f"❌ Invalid property name '{property_name}': only letters, digits, hyphens, and underscores are allowed"
            )]

        if property_value is not None:
            safe_value = property_value.replace('"', '\\"')
            dsl_query = f'[:find (pull ?p [*]) :where [?p :{property_name} "{safe_value}"]]'
        else:
            dsl_query = f"[:find (pull ?p [*]) :where [?p :{property_name} _]]"

        items = await client.query_dsl(dsl_query)

        if config.exclude_tags:
            all_pages = await client.get_all_pages()
            visible = filter_pages(all_pages, config.exclude_tags)
            visible_names = {(p.get("name") or "").lower() for p in visible}
            items = [
                it for it in items
                if (it.get("name") or it.get("originalName") or "").lower() in visible_names
            ]

        items = items[:limit]

        lines = [
            "🔍 **PAGES BY PROPERTY**",
            f"⚙️ Property: `{property_name}`"
            + (f" = `{property_value}`" if property_value is not None else ""),
            f"📊 Results: {len(items)}",
            "",
        ]

        if not items:
            lines.append("*(No pages found with this property)*")
        else:
            for item in items:
                name = item.get("originalName") or item.get("name") or str(item.get("uuid", "?"))
                uuid = item.get("uuid", "")
                lines.append(f"• 📄 {name}")
                if uuid:
                    lines.append(f"  🔑 UUID: {uuid}")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        return [TextContent(type="text", text=f"❌ Error finding pages by property: {exc}")]


async def find_pages_by_property(
    property_name: str,
    property_value: Optional[str] = None,
    limit: int = 100,
) -> List[TextContent]:
    """Find Logseq pages that have a specific property set.

    Args:
        property_name: Property key to search for (alphanumeric, hyphens, underscores).
        property_value: Optional exact value to match; omit to find all pages with the property.
        limit: Maximum number of results to return (default 100).

    Returns:
        List with one TextContent containing matching pages.

    Complexity: O(N) where N is result count.
    """
    cfg = load_config()
    return await _run(LogseqClient(cfg), cfg, property_name, property_value, limit)
