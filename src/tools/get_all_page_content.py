"""Get comprehensive content of a Logseq page."""

import json
import re
from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig
from src.privacy.exclude_tags import is_page_excluded
from src.tools.formatters.blocks import collect_block_uuids, format_block_tree
from src.logging_setup import get_logger


_log = get_logger(__name__)


_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def _looks_like_uuid(s: str) -> bool:
    """Return True if `s` matches the standard 8-4-4-4-12 hex UUID layout.

    @param s Candidate string.
    @returns True if it is a UUID.
    @complexity O(1).
    """
    return bool(_UUID_RE.fullmatch(s.lower()))


async def _resolve_identifier(
    client: LogseqClient,
    identifier: str,
    db_mode: bool,
) -> str:
    """Return a page name when the identifier is a UUID under DB mode (workaround for logseq#4920).

    @param client     Injected LogseqClient.
    @param identifier User-supplied page identifier (name or UUID).
    @param db_mode    Whether DB-mode is active.
    @returns          Page name string.
    @complexity O(1) network call when UUID, else no-op.
    """
    if not db_mode or not _looks_like_uuid(identifier):
        return identifier
    page = await client.get_page(identifier)
    if page and page.get("originalName"):
        return str(page["originalName"])
    return identifier


async def get_all_page_content(
    client: LogseqClient,
    config: LogseqConfig,
    page_identifier: str,
    fmt: str = "text",
    max_depth: int = -1,
    resolve_refs: bool = True,
) -> List[TextContent]:
    """Get comprehensive page content including all blocks and their full content.

    Args:
        client: LogseqClient instance (injected by the registry).
        config: LogseqConfig (provides db_mode flag and exclude_tags).
        page_identifier: The name or UUID of the page to get complete content from.
        fmt: Output format — "text" (default) or "json".
        max_depth: Maximum block nesting depth; -1 means unlimited.
        resolve_refs: When True and db_mode is enabled, resolve UUID block refs to names.

    Returns:
        List with one TextContent containing the full page content.

    Complexity: O(N) where N is total block count.
    """
    try:
        _log.debug("%s called", __name__)
        page_identifier = await _resolve_identifier(
            client, page_identifier, config.db_mode
        )
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
