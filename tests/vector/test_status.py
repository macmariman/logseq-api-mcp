"""Tests for vector_db_status tool."""

from unittest.mock import MagicMock, patch

import pytest

from src.vector.config import VectorConfig
from src.vector.status import vector_db_status


@pytest.fixture
def vector_config(tmp_path):
    return VectorConfig(
        db_path=tmp_path / "vector_db",
        graph_path=tmp_path / "graph",
    )


async def test_vector_db_status_disabled_when_not_configured():
    with patch("src.vector.status.load_vector_config", return_value=None):
        result = await vector_db_status()

    assert len(result) == 1
    assert "disabled" in result[0].text.lower() or "not enabled" in result[0].text.lower()


async def test_vector_db_status_reports_doc_count(vector_config):
    mock_table = MagicMock()
    mock_table.count_rows.return_value = 42
    mock_db = MagicMock()
    mock_db.open_table.return_value = mock_table

    with patch("src.vector.status.lancedb") as mock_lancedb, \
         patch("src.vector.status.load_vector_config", return_value=vector_config):
        mock_lancedb.connect.return_value = mock_db
        result = await vector_db_status()

    assert len(result) == 1
    assert "42" in result[0].text


async def test_vector_db_status_reports_not_synced_when_no_table(vector_config):
    mock_db = MagicMock()
    mock_db.open_table.side_effect = Exception("table not found")

    with patch("src.vector.status.lancedb") as mock_lancedb, \
         patch("src.vector.status.load_vector_config", return_value=vector_config):
        mock_lancedb.connect.return_value = mock_db
        result = await vector_db_status()

    assert len(result) == 1
    assert "not synced" in result[0].text.lower() or "sync" in result[0].text.lower()


async def test_vector_db_status_reports_lancedb_missing(vector_config):
    with patch("src.vector.status.lancedb", None), \
         patch("src.vector.status.load_vector_config", return_value=vector_config):
        result = await vector_db_status()

    assert len(result) == 1
    assert "not installed" in result[0].text.lower()
