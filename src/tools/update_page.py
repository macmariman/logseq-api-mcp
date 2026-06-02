"""Update an existing Logseq page by appending or replacing its content."""

from typing import Any, Dict, List, Optional
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig
from src.parser.markdown import parse_content
from src.logging_setup import get_logger
from src.tools._marker import hidden


_log = get_logger(__name__)


def _build_payload(
    content: Optional[str],
    properties: Optional[Dict[str, Any]],
) -> tuple[list[dict], dict[str, Any]]:
    """Parse content into batch blocks and merge with explicit properties.

    Args:
        content: Optional markdown source.
        properties: Optional explicit property dict (wins over frontmatter).

    Returns:
        Tuple of (batch_blocks, merged_properties).

    Complexity: O(N) where N is character count of content.
    """
    merged_props: dict[str, Any] = {}
    batch_blocks: list[dict] = []

    if content and content.strip():
        parsed = parse_content(content)
        if parsed.properties:
            merged_props.update(parsed.properties)
        batch_blocks = parsed.to_batch_format()

    if properties:
        merged_props.update(properties)

    return batch_blocks, merged_props


async def _clear_existing_blocks(client: LogseqClient, page_name: str) -> int:
    """Delete all top-level blocks of a page.

    Args:
        client: LogseqClient instance.
        page_name: Page identifier.

    Returns:
        Count of blocks deleted.

    Complexity: O(B) where B is top-level block count.
    """
    existing = await client.get_page_blocks_tree(page_name)
    deleted = 0
    for block in existing:
        block_uuid = block.get("uuid")
        if block_uuid:
            await client.delete_block(block_uuid)
            deleted += 1
    return deleted


def _summarize_actions(
    batch_blocks: list[dict],
    merged_props: dict[str, Any],
    mode: str,
) -> list[str]:
    """Build human-readable action descriptions.

    Args:
        batch_blocks: Blocks that were inserted.
        merged_props: Properties that were set.
        mode: "append" or "replace".

    Returns:
        List of action strings.

    Complexity: O(1).
    """
    actions: list[str] = []
    if batch_blocks:
        verb = "replaced" if mode == "replace" else "appended"
        actions.append(f"{len(batch_blocks)} block(s) {verb}")
    if merged_props:
        suffix = "ies" if len(merged_props) != 1 else "y"
        actions.append(f"{len(merged_props)} propert{suffix} set")
    return actions


def _format_summary(page_name: str, actions: list[str]) -> str:
    """Format the final success message.

    Args:
        page_name: Page that was updated.
        actions: Action descriptions from _summarize_actions.

    Returns:
        Multi-line summary string.

    Complexity: O(1).
    """
    summary = "; ".join(actions) if actions else "no changes"
    lines = [
        "✅ **PAGE UPDATED**",
        f"📄 Page: {page_name}",
        f"📝 {summary}",
    ]
    return "\n".join(lines)


# Hidden: file-mode-only setup; fs_write_page + fs_append cover page edits
# without the per-block API path. Reactivate for DB-mode/remote graphs.
@hidden
async def update_page(
    client: LogseqClient,
    config: LogseqConfig,
    page_name: str,
    content: Optional[str] = None,
    mode: str = "append",
    properties: Optional[Dict[str, Any]] = None,
) -> List[TextContent]:
    """Update an existing Logseq page by appending or replacing its content.

    Args:
        client: LogseqClient instance (injected by the registry).
        config: LogseqConfig (reserved for future use).
        page_name: Name of the page to update.
        content: Optional markdown content string; parsed into blocks.
        mode: "append" (default) adds blocks after existing; "replace" clears first.
        properties: Optional properties dict to set on the page.

    Returns:
        List with one TextContent describing success or failure.

    Complexity: O(B) where B is parsed block count.
    """
    try:
        _log.debug("%s called", __name__)
        if not content and not properties:
            return [
                TextContent(
                    type="text",
                    text="❌ Nothing to update: provide content or properties",
                )
            ]

        page = await client.get_page(page_name)
        if not page:
            return [TextContent(type="text", text=f"❌ Page '{page_name}' not found")]

        batch_blocks, merged_props = _build_payload(content, properties)

        if merged_props:
            await client.set_page_properties(page_name, merged_props)

        if mode == "replace" and batch_blocks:
            await _clear_existing_blocks(client, page_name)

        if batch_blocks:
            await client.insert_batch_block(page["uuid"], batch_blocks, sibling=False)

        actions = _summarize_actions(batch_blocks, merged_props, mode)
        return [TextContent(type="text", text=_format_summary(page_name, actions))]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error updating page: {exc}")]
