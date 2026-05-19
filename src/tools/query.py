"""Query the Logseq graph using Datalog DSL."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig, load_config
from src.privacy.exclude_tags import filter_pages
from src.logging_setup import get_logger


def _is_page_item(item: dict) -> bool:
    """Return True if the query result item represents a page."""
    return (
        "page" in item
        and "content" not in item
        or bool(item.get("page") and not item.get("uuid"))
    )


_log = get_logger(__name__)


async def _run(
    client: LogseqClient,
    config: LogseqConfig,
    query: str,
    limit: int = 100,
    result_type: str = "all",
) -> List[TextContent]:
    """Run a DSL query and format results using an injected client.

    Args:
        client: LogseqClient instance.
        config: LogseqConfig (provides exclude_tags).
        query: Datalog query string.
        limit: Maximum results to display.
        result_type: "all" | "pages_only" | "blocks_only".

    Returns:
        List with one TextContent containing formatted query results.

    Complexity: O(N) where N is result count.
    """
    try:
        _log.debug("%s called", __name__)
        items = await client.query_dsl(query)

        excluded_names: set[str] = set()
        if config.exclude_tags:
            all_pages = await client.get_all_pages()
            visible = filter_pages(all_pages, config.exclude_tags)
            visible_names = {(p.get("name") or "").lower() for p in visible}
            excluded_names = {
                (p.get("name") or "").lower() for p in all_pages
            } - visible_names

        def _page_name(item: dict) -> str:
            top = item.get("originalName") or item.get("name") or ""
            if top:
                return top.lower()
            page = item.get("page") or {}
            return (page.get("originalName") or page.get("name") or "").lower()

        def _is_excluded(item: dict) -> bool:
            return _page_name(item) in excluded_names

        items = [it for it in items if not _is_excluded(it)]

        page_items = [
            it for it in items if it.get("originalName") or it.get("page?") is not None
        ]
        block_items = [
            it for it in items if it.get("content") and not it.get("originalName")
        ]

        if result_type == "pages_only":
            display_items = page_items
        elif result_type == "blocks_only":
            display_items = block_items
        else:
            display_items = items

        display_items = display_items[:limit]

        lines = [
            "🔍 **QUERY RESULTS**",
            f"📝 Query: `{query}`",
            f"📊 Results: {len(display_items)} (of {len(items)} total)",
            "",
        ]

        if not display_items:
            lines.append("*(No results)*")
        else:
            for item in display_items:
                content = item.get("content", "").strip()
                page = item.get("page") or {}
                page_name = page.get("originalName") or page.get("name") or ""
                uuid = item.get("uuid", "")

                top_name = item.get("originalName") or item.get("name") or ""
                if top_name:
                    lines.append(f"• 📄 {top_name}")
                    if uuid:
                        lines.append(f"  🔑 UUID: {uuid}")
                elif content:
                    lines.append(f"• 📝 {content[:120]}")
                    if page_name:
                        lines.append(f"  📄 Page: {page_name}")
                    if uuid:
                        lines.append(f"  🔑 UUID: {uuid}")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error running query: {exc}")]


async def query(
    query: str,
    limit: int = 100,
    result_type: str = "all",
) -> List[TextContent]:
    """Query the Logseq graph using Datalog DSL syntax.

    Args:
        query: Datalog query string (e.g. '[:find ?b :where [?b :block/content ?c]]').
        limit: Maximum number of results to return (default 100).
        result_type: Filter results — "all" (default), "pages_only", or "blocks_only".

    Returns:
        List with one TextContent containing formatted query results.

    Complexity: O(N) where N is result count.
    """
    cfg = load_config()
    return await _run(LogseqClient(cfg), cfg, query, limit, result_type)
