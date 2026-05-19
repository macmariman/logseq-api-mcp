"""VectorConfig dataclass and loader for optional vector search."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class VectorConfig:
    db_path: Path
    graph_path: Path
    exclude_tags: List[str] = field(default_factory=list)
    chunk_size: int = 512
    watch_debounce: float = 2.0


def load_vector_config() -> Optional[VectorConfig]:
    """Return VectorConfig when LOGSEQ_VECTOR_ENABLED is truthy, else None."""
    enabled_raw = os.getenv("LOGSEQ_VECTOR_ENABLED", "").strip().lower()
    if enabled_raw not in ("1", "true", "yes"):
        return None

    db_path = Path(
        os.getenv(
            "LOGSEQ_VECTOR_PATH",
            str(Path.home() / ".cache" / "logseq-api-mcp" / "vector_db"),
        )
    )
    graph_path = Path(os.getenv("LOGSEQ_GRAPH_PATH", str(Path.home() / "logseq")))

    exclude_raw = os.getenv("LOGSEQ_EXCLUDE_TAGS", "")
    exclude_tags = [t.strip() for t in exclude_raw.split(",") if t.strip()]

    return VectorConfig(
        db_path=db_path,
        graph_path=graph_path,
        exclude_tags=exclude_tags,
    )
