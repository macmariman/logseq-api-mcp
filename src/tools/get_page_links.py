"""Get pages that link to a specified Logseq page (backlinks)."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import load_config
from src.tools.formatters.pages import format_timestamp


def _format_linking_page(
    page_ref: dict, full_page: dict | None, ref_count: int
) -> list[str]:
    """Format a single linking-page entry.

    Args:
        page_ref: Raw reference dict from getPageLinkedReferences.
        full_page: Full page dict for metadata enrichment (or None).
        ref_count: Number of blocks in this page that reference the target.

    Returns:
        List of display lines.

    Complexity: O(1).
    """
    ref_name = page_ref.get("originalName") or page_ref.get("name", "Unknown")
    ref_id = page_ref.get("id", "N/A")
    is_journal = False
    uuid = "N/A"
    created = "N/A"
    updated = "N/A"

    if full_page:
        is_journal = full_page.get("journal?", False)
        uuid = full_page.get("uuid", "N/A")
        created = format_timestamp(full_page.get("createdAt"))
        updated = format_timestamp(full_page.get("updatedAt"))

    emoji = "📅" if is_journal else "📄"
    return [
        f"{emoji} **{ref_name}**",
        f"   🔑 ID: {ref_id} | UUID: {uuid}",
        f"   📊 References: {ref_count} | Journal: {'Yes' if is_journal else 'No'}",
        f"   📅 Created: {created}",
        f"   🔄 Updated: {updated}",
        "",
    ]


async def _run(client: LogseqClient, page_identifier: str) -> List[TextContent]:
    """Fetch and format backlinks using an injected client.

    Args:
        client: LogseqClient instance.
        page_identifier: The name or UUID of the target page.

    Returns:
        List with one TextContent containing the backlink analysis.

    Complexity: O(P + R) where P is page count, R is reference count.
    """
    try:
        linked_refs = await client.get_page_linked_references(page_identifier)
        if not linked_refs:
            return [TextContent(type="text", text=f"✅ No pages link to '{page_identifier}'")]

        all_pages = await client.get_all_pages()
        page_lookup = {
            p.get("id"): p for p in all_pages if isinstance(p, dict) and p.get("id")
        }

        enriched: list[dict] = []
        for group in linked_refs:
            if not isinstance(group, list) or len(group) < 1:
                continue
            page_ref = group[0]
            if not isinstance(page_ref, dict):
                continue
            ref_id = page_ref.get("id")
            ref_count = len(group) - 1
            enriched.append({
                "ref": page_ref,
                "full": page_lookup.get(ref_id),
                "count": ref_count,
            })

        enriched.sort(key=lambda e: (-e["count"], (e["ref"].get("name") or "").lower()))

        lines = [
            "🔗 **PAGE LINKS ANALYSIS**",
            f"📄 Target Page: {page_identifier}",
            f"📊 Found {len(enriched)} linking pages",
            "",
            "🎯 **LINKING PAGES:**",
            "",
        ]
        for entry in enriched:
            lines.extend(_format_linking_page(entry["ref"], entry["full"], entry["count"]))

        journal_count = sum(
            1 for e in enriched if (e["full"] or {}).get("journal?", False)
        )
        total_refs = sum(e["count"] for e in enriched)
        lines.extend([
            "📈 **SUMMARY:**",
            f"• Total linking pages: {len(enriched)}",
            f"• Journal pages: {journal_count}",
            f"• Regular pages: {len(enriched) - journal_count}",
            f"• Total references: {total_refs}",
        ])

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        return [TextContent(type="text", text=f"❌ Error fetching page links: {exc}")]


async def get_page_links(page_identifier: str) -> List[TextContent]:
    """Get pages that link to the specified page with comprehensive metadata.

    Args:
        page_identifier: The name or UUID of the page to find links to.

    Returns:
        List with one TextContent containing the backlink analysis.

    Complexity: O(P + R) where P is page count, R is reference count.
    """
    return await _run(LogseqClient(load_config()), page_identifier)
