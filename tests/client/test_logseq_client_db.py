"""Tests for LogseqClient DB-mode methods."""

from unittest.mock import AsyncMock, patch

import pytest

from src.client.config import LogseqConfig
from src.client.logseq_client import LogseqClient


@pytest.fixture
def config():
    return LogseqConfig(endpoint="http://localhost:12315/api", token="test-tok", db_mode=True)


@pytest.fixture
def client(config):
    return LogseqClient(config)


@pytest.fixture
def mock_call(client):
    with patch.object(client, "_call", new_callable=AsyncMock) as mock:
        yield mock


# ── datascript_query ──────────────────────────────────────────────────────────

async def test_datascript_query_sends_correct_payload(client, mock_call):
    mock_call.return_value = [[1], [2]]
    result = await client.datascript_query("[:find ?e :where [?e :page/name]]")
    mock_call.assert_awaited_once_with(
        "logseq.DB.datascriptQuery",
        ["[:find ?e :where [?e :page/name]]"],
    )
    assert result == [[1], [2]]


async def test_datascript_query_returns_empty_list_on_none(client, mock_call):
    mock_call.return_value = None
    result = await client.datascript_query("[:find ?e]")
    assert result == []


# ── resolve_page_uuids ────────────────────────────────────────────────────────

async def test_resolve_page_uuids_batches_requests(client, mock_call):
    """One _call per UUID — result keyed by uuid."""
    mock_call.side_effect = [
        {"originalName": "Page Alpha", "name": "page-alpha"},
        {"originalName": "Page Beta", "name": "page-beta"},
    ]
    uuids = ["uuid-1", "uuid-2"]
    result = await client.resolve_page_uuids(uuids)
    assert mock_call.await_count == 2
    assert result == {"uuid-1": "Page Alpha", "uuid-2": "Page Beta"}


async def test_resolve_page_uuids_skips_missing(client, mock_call):
    """UUIDs that return None are omitted from the result."""
    mock_call.side_effect = [None, {"originalName": "Found", "name": "found"}]
    result = await client.resolve_page_uuids(["missing", "present"])
    assert "missing" not in result
    assert result["present"] == "Found"


async def test_resolve_page_uuids_empty_input(client, mock_call):
    result = await client.resolve_page_uuids([])
    assert result == {}
    mock_call.assert_not_awaited()


# ── get_blocks_db_properties ──────────────────────────────────────────────────

async def test_get_blocks_db_properties_returns_keyed_dict(client, mock_call):
    blocks = [
        {"uuid": "b1", "properties": {"status": "done", "priority": "A"}},
        {"uuid": "b2", "properties": {"status": "todo"}},
    ]
    result = await client.get_blocks_db_properties(blocks)
    assert result["b1"] == {"status": "done", "priority": "A"}
    assert result["b2"] == {"status": "todo"}


async def test_get_blocks_db_properties_strips_logseq_internal_keys(client, mock_call):
    blocks = [{"uuid": "b1", "properties": {"status": "done", ":logseq.internal": "x"}}]
    result = await client.get_blocks_db_properties(blocks)
    assert ":logseq.internal" not in result.get("b1", {})
    assert result["b1"]["status"] == "done"


async def test_get_blocks_db_properties_skips_blocks_without_uuid(client, mock_call):
    blocks = [{"properties": {"status": "done"}}, {"uuid": "b2", "properties": {}}]
    result = await client.get_blocks_db_properties(blocks)
    assert len(result) == 0


# ── resolve_property_ident ────────────────────────────────────────────────────

async def test_resolve_property_ident_returns_ident_on_match(client, mock_call):
    mock_call.return_value = [["status"]]
    result = await client.resolve_property_ident("status")
    assert result == "status"


async def test_resolve_property_ident_returns_none_on_unknown(client, mock_call):
    mock_call.return_value = []
    result = await client.resolve_property_ident("nonexistent")
    assert result is None


async def test_resolve_property_ident_uses_datascript_query(client, mock_call):
    mock_call.return_value = []
    await client.resolve_property_ident("status")
    call_args = mock_call.call_args
    assert call_args[0][0] == "logseq.DB.datascriptQuery"
    assert "status" in call_args[0][1][0]
