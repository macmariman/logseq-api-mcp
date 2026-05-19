"""Semantic vector search tool for Logseq blocks."""

from __future__ import annotations

from typing import List

from mcp.types import TextContent

from src.vector.config import load_vector_config
from src.logging_setup import get_logger

try:
    import lancedb  # type: ignore[import]
except ImportError:
    lancedb = None  # type: ignore[assignment]

_log = get_logger(__name__)

_TABLE_NAME = "blocks"


async def vector_search(
    query: str,
    limit: int = 10,
) -> List[TextContent]:
    """Search Logseq blocks using semantic vector similarity.

    Args:
        query: Natural-language query to embed and search.
        limit: Maximum number of results to return (default 10).

    Returns:
        List with one TextContent containing ranked results.
    """
    cfg = load_vector_config()
    if cfg is None:
        return [
            TextContent(
                type="text",
                text="ℹ️ Vector search not enabled. Set LOGSEQ_VECTOR_ENABLED=true and run logseq-sync.",
            )
        ]

    if lancedb is None:
        return [
            TextContent(
                type="text",
                text="❌ lancedb not installed. Install with: uv sync --group vector",
            )
        ]

    try:
        db = lancedb.connect(str(cfg.db_path))
        table = db.open_table(_TABLE_NAME)
    except Exception as exc:
        _log.error("vector_search: cannot open table: %s", exc)
        return [
            TextContent(
                type="text",
                text=f"❌ Vector DB not found or not synced: {exc}\nRun: logseq-sync --once",
            )
        ]

    try:
        rows = table.search(query).limit(limit).to_list()
    except Exception as exc:
        _log.error("vector_search: query failed: %s", exc)
        return [TextContent(type="text", text=f"❌ Vector search failed: {exc}")]

    if not rows:
        return [TextContent(type="text", text=f"No vector results found for: {query}")]

    lines = [f"🔍 **Vector search results** for: `{query}`\n"]
    for i, row in enumerate(rows, 1):
        page = row.get("page", "?")
        text = row.get("text", "")[:200]
        score = row.get("_distance", "?")
        score_str = f"{score:.4f}" if isinstance(score, float) else str(score)
        lines.append(f"**{i}. {page}** (distance: {score_str})")
        lines.append(f"   {text}")
        lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]
