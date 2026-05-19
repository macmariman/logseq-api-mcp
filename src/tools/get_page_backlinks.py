"""Get pages that link to a specified Logseq page (backlinks)."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig
from src.tools.formatters.pages import format_timestamp
from src.logging_setup import get_logger


def _format_linking_page(
    page_ref: dict,
    full_page: dict | None,
    ref_blocks: list[dict],
    include_content: bool,
) -> list[str]:
    """Format a single linking-page entry with optional block content.

    Args:
        page_ref: Raw reference dict from getPageLinkedReferences.
        full_page: Full page dict for metadata enrichment (or None).
        ref_blocks: Block dicts from this page that reference the target.
        include_content: When True, include the content of referencing blocks.

    Returns:
        List of display lines.

    Complexity: O(B) where B is referencing block count.
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
    lines = [
        f"{emoji} **{ref_name}**",
        f"   🔑 ID: {ref_id} | UUID: {uuid}",
        f"   📊 References: {len(ref_blocks)} | Journal: {'Yes' if is_journal else 'No'}",
        f"   📅 Created: {created}",
        f"   🔄 Updated: {updated}",
    ]

    if include_content:
        for block in ref_blocks:
            content = block.get("content", "").strip()
            if content:
                lines.append(f"   💬 {content}")

    lines.append("")
    return lines


_log = get_logger(__name__)


async def get_page_backlinks(
    client: LogseqClient,
    config: LogseqConfig,
    page_identifier: str,
    include_content: bool = True,
) -> List[TextContent]:
    """Get pages that link to the specified page with comprehensive metadata.

    Args:
        client: LogseqClient instance (injected by the registry).
        config: LogseqConfig (provides exclude_tags for privacy filtering).
        page_identifier: The name or UUID of the page to find backlinks for.
        include_content: When True, include the text of each referencing block.

    Returns:
        List with one TextContent containing the backlink analysis.

    Complexity: O(P + R) where P is page count, R is reference count.
    """
    try:
        _log.debug("%s called", __name__)
        linked_refs = await client.get_page_linked_references(page_identifier)
        if not linked_refs:
            return [
                TextContent(
                    type="text", text=f"✅ No pages link to '{page_identifier}'"
                )
            ]

        excluded_names: frozenset[str] = await client.excluded_page_names()

        enriched: list[dict] = []
        for group in linked_refs:
            if not isinstance(group, list) or len(group) < 1:
                continue
            page_ref = group[0]
            if not isinstance(page_ref, dict):
                continue
            ref_name = (
                page_ref.get("originalName") or page_ref.get("name") or ""
            ).lower()
            if excluded_names and ref_name in excluded_names:
                continue
            ref_blocks = [b for b in group[1:] if isinstance(b, dict)]
            enriched.append(
                {
                    "ref": page_ref,
                    "full": None,
                    "blocks": ref_blocks,
                }
            )

        enriched.sort(
            key=lambda e: (-len(e["blocks"]), (e["ref"].get("name") or "").lower())
        )

        lines = [
            "🔗 **PAGE BACKLINKS**",
            f"📄 Target Page: {page_identifier}",
            f"📊 Found {len(enriched)} linking pages",
            "",
            "🎯 **LINKING PAGES:**",
            "",
        ]
        for entry in enriched:
            lines.extend(
                _format_linking_page(
                    entry["ref"], entry["full"], entry["blocks"], include_content
                )
            )

        journal_count = sum(
            1 for e in enriched if (e["full"] or {}).get("journal?", False)
        )
        total_refs = sum(len(e["blocks"]) for e in enriched)
        lines.extend(
            [
                "📈 **SUMMARY:**",
                f"• Total linking pages: {len(enriched)}",
                f"• Journal pages: {journal_count}",
                f"• Regular pages: {len(enriched) - journal_count}",
                f"• Total references: {total_refs}",
            ]
        )

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [
            TextContent(type="text", text=f"❌ Error fetching page backlinks: {exc}")
        ]
