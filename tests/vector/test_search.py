"""Tests for vector_search tool."""

from unittest.mock import MagicMock, patch

import pytest

from src.vector.config import VectorConfig
from src.vector.search import vector_search


@pytest.fixture
def vector_config(tmp_path):
    return VectorConfig(
        db_path=tmp_path / "vector_db",
        graph_path=tmp_path / "graph",
    )


async def test_vector_search_returns_results_when_available(vector_config):
    mock_results = [
        {
            "page": "Alpha",
            "chunk_index": 0,
            "text": "Block one Block two",
            "_distance": 0.1,
        },
        {"page": "Beta", "chunk_index": 0, "text": "Hello world", "_distance": 0.2},
    ]
    mock_table = MagicMock()
    mock_table.search.return_value.limit.return_value.to_list.return_value = (
        mock_results
    )
    mock_db = MagicMock()
    mock_db.open_table.return_value = mock_table

    with (
        patch("src.vector.search.lancedb") as mock_lancedb,
        patch("src.vector.search.load_vector_config", return_value=vector_config),
    ):
        mock_lancedb.connect.return_value = mock_db
        result = await vector_search("hello")

    assert len(result) == 1
    assert "Alpha" in result[0].text
    assert "Beta" in result[0].text


async def test_vector_search_returns_disabled_message_when_not_configured():
    with patch("src.vector.search.load_vector_config", return_value=None):
        result = await vector_search("anything")

    assert len(result) == 1
    assert (
        "not enabled" in result[0].text.lower() or "disabled" in result[0].text.lower()
    )


async def test_vector_search_returns_error_when_lancedb_missing(vector_config):
    with (
        patch("src.vector.search.lancedb", None),
        patch("src.vector.search.load_vector_config", return_value=vector_config),
    ):
        result = await vector_search("hello")

    assert len(result) == 1
    assert (
        "not installed" in result[0].text.lower()
        or "unavailable" in result[0].text.lower()
    )


async def test_vector_search_handles_open_table_failure(vector_config):
    mock_db = MagicMock()
    mock_db.open_table.side_effect = Exception("table not found")

    with (
        patch("src.vector.search.lancedb") as mock_lancedb,
        patch("src.vector.search.load_vector_config", return_value=vector_config),
    ):
        mock_lancedb.connect.return_value = mock_db
        result = await vector_search("test")

    assert len(result) == 1
    assert (
        "❌" in result[0].text
        or "no results" in result[0].text.lower()
        or "not found" in result[0].text.lower()
    )


async def test_vector_search_respects_limit(vector_config):
    mock_results = [
        {
            "page": f"Page{i}",
            "chunk_index": 0,
            "text": f"text {i}",
            "_distance": float(i) * 0.1,
        }
        for i in range(5)
    ]
    mock_table = MagicMock()
    mock_table.search.return_value.limit.return_value.to_list.return_value = (
        mock_results
    )
    mock_db = MagicMock()
    mock_db.open_table.return_value = mock_table

    with (
        patch("src.vector.search.lancedb") as mock_lancedb,
        patch("src.vector.search.load_vector_config", return_value=vector_config),
    ):
        mock_lancedb.connect.return_value = mock_db
        await vector_search("test", limit=5)

    mock_table.search.return_value.limit.assert_called_with(5)
