"""Get pages under a Logseq namespace formatted as an ASCII tree."""

from typing import List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import LogseqConfig, load_config
from src.tools.formatters.pages import format_namespace_tree


async def _run(
    client: LogseqClient,
    config: LogseqConfig,
    namespace: str,
) -> List[TextContent]:
    """Fetch and tree-format a namespace hierarchy using an injected client.

    Args:
        client: LogseqClient instance.
        config: LogseqConfig (reserved for future use).
        namespace: The namespace prefix to display as a tree.

    Returns:
        List with one TextContent containing the ASCII tree.

    Complexity: O(N) where N is total node count.
    """
    try:
        pages = await client.get_pages_tree_from_namespace(namespace)

        lines = [
            "🌳 **NAMESPACE TREE**",
            f"🗂️ Namespace: {namespace}",
            "",
        ]

        if not pages:
            lines.append(f"*(No pages found under namespace '{namespace}')*")
        else:
            lines.extend(format_namespace_tree(pages))

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        return [TextContent(type="text", text=f"❌ Error fetching namespace tree: {exc}")]


async def get_pages_tree_from_namespace(namespace: str) -> List[TextContent]:
    """Get pages under a Logseq namespace displayed as an ASCII tree.

    Args:
        namespace: The namespace prefix to display (e.g. "Project").

    Returns:
        List with one TextContent containing the ASCII tree.

    Complexity: O(N) where N is total node count.
    """
    cfg = load_config()
    return await _run(LogseqClient(cfg), cfg, namespace)
