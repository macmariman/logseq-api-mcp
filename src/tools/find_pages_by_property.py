"""Find Logseq pages that have a specific property (and optionally a specific value)."""

import re
from typing import List, Optional
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig
from src.logging_setup import get_logger

_VALID_PROP_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")
_VALUE_MAX = 256


_log = get_logger(__name__)


def _escape_dsl_value(value: str) -> str:
    """Escape a value for safe embedding inside a Logseq DSL double-quoted string.

    Backslashes are escaped first so subsequent quote-escaping does not double-escape
    the backslashes we just added.
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')


async def find_pages_by_property(
    client: LogseqClient,
    config: LogseqConfig,
    property_name: str,
    property_value: Optional[str] = None,
    limit: int = 100,
) -> List[TextContent]:
    """Find Logseq pages that have a specific property set.

    Args:
        client: LogseqClient instance (injected by the registry).
        config: LogseqConfig (provides exclude_tags).
        property_name: Property key to search for (alphanumeric, hyphens, underscores).
        property_value: Optional exact value to match; omit to find all pages with the property.
        limit: Maximum number of results to return (default 100).

    Returns:
        List with one TextContent containing matching pages.

    Complexity: O(N) where N is result count.
    """
    try:
        _log.debug("%s called", __name__)
        if property_value is not None and len(property_value) > _VALUE_MAX:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Property value exceeds maximum length of {_VALUE_MAX} characters (got {len(property_value)})",
                )
            ]

        if not _VALID_PROP_RE.match(property_name):
            return [
                TextContent(
                    type="text",
                    text=f"❌ Invalid property name '{property_name}': only letters, digits, dots, hyphens, and underscores are allowed",
                )
            ]

        if property_value is not None:
            safe_value = _escape_dsl_value(property_value)
            dsl_query = (
                f'[:find (pull ?p [*]) :where [?p :{property_name} "{safe_value}"]]'
            )
        else:
            dsl_query = f"[:find (pull ?p [*]) :where [?p :{property_name} _]]"

        items = await client.query_dsl(dsl_query)

        excluded_names: frozenset[str] = await client.excluded_page_names()
        if excluded_names:
            items = [
                it
                for it in items
                if (it.get("name") or it.get("originalName") or "").lower()
                not in excluded_names
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
                name = (
                    item.get("originalName")
                    or item.get("name")
                    or str(item.get("uuid", "?"))
                )
                uuid = item.get("uuid", "")
                lines.append(f"• 📄 {name}")
                if uuid:
                    lines.append(f"  🔑 UUID: {uuid}")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [
            TextContent(type="text", text=f"❌ Error finding pages by property: {exc}")
        ]
