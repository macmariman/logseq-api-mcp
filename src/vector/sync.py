"""Graph sync daemon for vector search."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Iterator, List

from src.vector.config import VectorConfig
from src.logging_setup import get_logger

try:
    import lancedb  # type: ignore[import]
except ImportError:
    lancedb = None  # type: ignore[assignment]

_log = get_logger(__name__)

_TABLE_NAME = "blocks"


def _chunk_text(text: str, chunk_size: int = 512) -> List[str]:
    """Split text into chunks of at most chunk_size characters, respecting word boundaries."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    words = text.split()
    current: List[str] = []
    current_len = 0

    for word in words:
        if current_len + len(word) + (1 if current else 0) > chunk_size and current:
            chunks.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            if current:
                current_len += 1 + len(word)
            else:
                current_len = len(word)
            current.append(word)

    if current:
        chunks.append(" ".join(current))

    return chunks


def _iter_markdown_files(graph_path: Path) -> Iterator[Path]:
    """Yield all .md files under graph_path recursively."""
    yield from graph_path.rglob("*.md")


def _build_rows(graph_path: Path, chunk_size: int) -> List[dict]:
    """Parse markdown files and return list of row dicts for LanceDB."""
    rows: List[dict] = []
    for md_file in _iter_markdown_files(graph_path):
        page_name = md_file.stem
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, chunk in enumerate(_chunk_text(text, chunk_size)):
            rows.append(
                {
                    "page": page_name,
                    "chunk_index": i,
                    "text": chunk,
                }
            )
    return rows


def sync_graph(config: VectorConfig) -> None:
    """Scan markdown files, chunk, and upsert into LanceDB.

    Args:
        config: VectorConfig with db_path, graph_path, chunk_size.
    """
    if lancedb is None:
        _log.warning("lancedb not installed; skipping sync_graph")
        return

    config.db_path.mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(str(config.db_path))

    rows = _build_rows(config.graph_path, config.chunk_size)

    try:
        table = db.open_table(_TABLE_NAME)
        if rows:
            table.add(rows)
    except Exception:
        if rows:
            db.create_table(_TABLE_NAME, data=rows)
        else:
            _log.debug("No markdown files found; skipping table creation")

    _log.info("sync_graph: synced %d chunks from %s", len(rows), config.graph_path)


def watch_graph(config: VectorConfig) -> None:
    """Watch graph_path for changes and re-sync on modification.

    Uses watchdog if available; falls back to polling every watch_debounce seconds.

    Args:
        config: VectorConfig with graph_path and watch_debounce.
    """
    try:
        from watchdog.observers import Observer  # type: ignore[import]
        from watchdog.events import FileSystemEventHandler  # type: ignore[import]

        class _Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if not event.is_directory and event.src_path.endswith(".md"):
                    _log.info("Change detected: %s", event.src_path)
                    sync_graph(config)

        observer = Observer()
        observer.schedule(_Handler(), str(config.graph_path), recursive=True)
        observer.start()
        _log.info("watch_graph: watching %s", config.graph_path)
        try:
            while True:
                time.sleep(config.watch_debounce)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
    except ImportError:
        _log.warning("watchdog not installed; falling back to polling")
        while True:
            sync_graph(config)
            time.sleep(config.watch_debounce)


def cli_entry() -> None:
    """CLI entry point for logseq-sync command."""
    import argparse

    from src.vector.config import load_vector_config

    parser = argparse.ArgumentParser(description="Sync Logseq graph into vector DB")
    parser.add_argument("--once", action="store_true", help="Run one sync then exit")
    args = parser.parse_args()

    cfg = load_vector_config()
    if cfg is None:
        print("Vector search not enabled. Set LOGSEQ_VECTOR_ENABLED=true.")
        return

    if args.once:
        sync_graph(cfg)
    else:
        watch_graph(cfg)
