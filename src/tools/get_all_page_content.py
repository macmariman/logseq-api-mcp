"""Get comprehensive content of a Logseq page."""

import json
from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig, load_config
from src.privacy.exclude_tags import is_page_excluded
from src.tools.formatters.blocks import collect_block_uuids, format_block_tree
from src.logging_setup import get_logger


_log = get_logger(__name__)


async def _run(
    client: LogseqClient,
    config: LogseqConfig,
    page_identifier: str,
    fmt: str = "text",
    max_depth: int = -1,
    resolve_refs: bool = True,
) -> List[TextContent]:
    """Fetch and format full page content using an injected client.

    Args:
        client: LogseqClient instance.
        config: LogseqConfig (provides db_mode flag).
        page_identifier: The name or UUID of the page to get content from.
        fmt: Output format — "text" (default) or "json".
        max_depth: Maximum block nesting depth; -1 means unlimited.
        resolve_refs: When True and db_mode, resolve UUID references to page names.

    Returns:
        List with one TextContent containing the full page content.

    Complexity: O(N) where N is total block count.
    """
    try:
        _log.debug("%s called", __name__)
        page = await client.get_page(page_identifier)
        blocks = await client.get_page_blocks_tree(page_identifier)

        if not page and not blocks:
            return [
                TextContent(type="text", text=f"❌ Page '{page_identifier}' not found")
            ]

        if config.exclude_tags and page and is_page_excluded(page, config.exclude_tags):
            return [
                TextContent(
                    type="text",
                    text=f"❌ Access denied: page '{page_identifier}' is excluded by tag policy",
                )
            ]

        page_name = (page or {}).get("originalName") or (page or {}).get(
            "name", page_identifier
        )
        page_id = (page or {}).get("id", "N/A")
        page_uuid = (page or {}).get("uuid", "N/A")

        uuid_map: dict[str, str] = {}
        if config.db_mode and resolve_refs and blocks:
            uuids = collect_block_uuids(blocks)
            if uuids:
                uuid_map = await client.resolve_page_uuids(list(uuids))

        if fmt == "json":

            def _block_to_dict(block: dict, depth: int) -> dict:
                if max_depth != -1 and depth > max_depth:
                    return {}
                return {
                    "uuid": block.get("uuid"),
                    "content": block.get("content", ""),
                    "children": [
                        _block_to_dict(c, depth + 1)
                        for c in block.get("children", [])
                        if max_depth == -1 or depth + 1 <= max_depth
                    ],
                }

            payload = {
                "page": {
                    "name": page_name,
                    "id": page_id,
                    "uuid": page_uuid,
                },
                "blocks": [_block_to_dict(b, 0) for b in blocks],
            }
            return [
                TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))
            ]

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
                lines.extend(
                    format_block_tree(
                        block, level=0, max_level=max_depth, uuid_map=uuid_map or None
                    )
                )

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error fetching page content: {exc}")]


async def get_all_page_content(
    page_identifier: str,
    fmt: str = "text",
    max_depth: int = -1,
    resolve_refs: bool = True,
) -> List[TextContent]:
    """Get comprehensive page content including all blocks and their full content.

    Args:
        page_identifier: The name or UUID of the page to get complete content from.
        fmt: Output format — "text" (default) or "json".
        max_depth: Maximum block nesting depth; -1 means unlimited.
        resolve_refs: When True and db_mode is enabled, resolve UUID block refs to names.

    Returns:
        List with one TextContent containing the full page content.

    Complexity: O(N) where N is total block count.
    """
    cfg = load_config()
    return await _run(
        LogseqClient(cfg), cfg, page_identifier, fmt, max_depth, resolve_refs
    )
