"""Vector DB status reporting tool."""

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


async def vector_db_status() -> List[TextContent]:
    """Report vector DB status: enabled, path, document count, sync state.

    Returns:
        List with one TextContent containing status information.
    """
    cfg = load_vector_config()
    if cfg is None:
        return [TextContent(
            type="text",
            text="ℹ️ **Vector Search Status**: disabled\nSet LOGSEQ_VECTOR_ENABLED=true to enable.",
        )]

    if lancedb is None:
        return [TextContent(
            type="text",
            text=(
                "⚠️ **Vector Search Status**: enabled (config found) but lancedb not installed\n"
                "Install with: uv sync --group vector"
            ),
        )]

    lines = [
        "📊 **Vector DB Status**",
        f"✅ Enabled: yes",
        f"📁 DB path: {cfg.db_path}",
        f"📂 Graph path: {cfg.graph_path}",
    ]

    try:
        db = lancedb.connect(str(cfg.db_path))
        table = db.open_table(_TABLE_NAME)
        doc_count = table.count_rows()
        lines.append(f"📝 Documents: {doc_count}")
        lines.append("🔄 Status: synced")
    except Exception as exc:
        _log.debug("vector_db_status: table not found: %s", exc)
        lines.append("📝 Documents: 0")
        lines.append("⚠️ Status: not synced — run: logseq-sync --once")

    return [TextContent(type="text", text="\n".join(lines))]
