"""Update an existing Logseq page by appending or replacing its content."""

from typing import Any, Dict, List, Optional
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig
from src.parser.markdown import parse_content
from src.logging_setup import get_logger


_log = get_logger(__name__)


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

        merged_props: dict[str, Any] = {}
        batch_blocks: list[dict] = []

        if content and content.strip():
            parsed = parse_content(content)
            if parsed.properties:
                merged_props.update(parsed.properties)
            batch_blocks = parsed.to_batch_format()

        if properties:
            merged_props.update(properties)

        if merged_props:
            await client.set_page_properties(page_name, merged_props)

        if mode == "replace" and batch_blocks:
            existing = await client.get_page_blocks_tree(page_name)
            for block in existing:
                block_uuid = block.get("uuid")
                if block_uuid:
                    await client.delete_block(block_uuid)

        actions: list[str] = []

        if batch_blocks:
            await client.append_block_in_page(
                page_name, batch_blocks[0].get("content", "")
            )
            for block in batch_blocks[1:]:
                await client.append_block_in_page(page_name, block.get("content", ""))
            actions.append(
                f"{len(batch_blocks)} block(s) {'replaced' if mode == 'replace' else 'appended'}"
            )

        if merged_props:
            actions.append(
                f"{len(merged_props)} propert{'ies' if len(merged_props) != 1 else 'y'} set"
            )

        summary = "; ".join(actions) if actions else "no changes"
        lines = [
            "✅ **PAGE UPDATED**",
            f"📄 Page: {page_name}",
            f"📝 {summary}",
        ]
        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error updating page: {exc}")]
