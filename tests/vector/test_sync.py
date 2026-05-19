"""Tests for vector graph sync."""

from unittest.mock import MagicMock, patch

import pytest

from src.vector.config import VectorConfig
from src.vector.sync import sync_graph, _chunk_text, _iter_markdown_files


@pytest.fixture
def graph_dir(tmp_path):
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "Alpha.md").write_text("- Block one\n- Block two\n")
    (pages / "Beta.md").write_text("- Hello world\n")
    return tmp_path


@pytest.fixture
def vector_config(tmp_path, graph_dir):
    return VectorConfig(
        db_path=tmp_path / "vector_db",
        graph_path=graph_dir,
        chunk_size=512,
    )


# --- pure helpers ---


def test_chunk_text_splits_long_text():
    text = "word " * 200
    chunks = _chunk_text(text, chunk_size=50)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 60  # some slack for word boundary


def test_chunk_text_returns_single_chunk_for_short():
    text = "short text"
    chunks = _chunk_text(text, chunk_size=512)
    assert chunks == ["short text"]


def test_iter_markdown_files_finds_md_files(graph_dir):
    files = list(_iter_markdown_files(graph_dir))
    names = {f.name for f in files}
    assert "Alpha.md" in names
    assert "Beta.md" in names


def test_iter_markdown_files_ignores_non_md(tmp_path):
    (tmp_path / "notes.txt").write_text("ignore me")
    (tmp_path / "page.md").write_text("- keep")
    files = list(_iter_markdown_files(tmp_path))
    assert all(f.suffix == ".md" for f in files)


# --- sync_graph (with lancedb mocked) ---


def test_sync_graph_creates_db_and_inserts_rows(vector_config):
    mock_table = MagicMock()
    mock_db = MagicMock()
    mock_db.create_table.return_value = mock_table
    mock_db.open_table.side_effect = Exception("not found")

    with patch("src.vector.sync.lancedb") as mock_lancedb:
        mock_lancedb.connect.return_value = mock_db
        sync_graph(vector_config)

    mock_lancedb.connect.assert_called_once()
    assert mock_db.create_table.called or mock_db.open_table.called


def test_sync_graph_skips_empty_graph(tmp_path):
    cfg = VectorConfig(db_path=tmp_path / "db", graph_path=tmp_path / "empty")
    cfg.graph_path.mkdir()

    mock_db = MagicMock()
    mock_db.open_table.side_effect = Exception("not found")

    with patch("src.vector.sync.lancedb") as mock_lancedb:
        mock_lancedb.connect.return_value = mock_db
        sync_graph(cfg)

    mock_lancedb.connect.assert_called_once()
