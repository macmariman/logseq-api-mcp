"""Tests for LogseqClient DB-mode methods."""

from unittest.mock import AsyncMock, patch

import pytest

from src.client.config import LogseqConfig
from src.client.logseq_client import LogseqClient


@pytest.fixture
def config():
    return LogseqConfig(
        endpoint="http://localhost:12315/api", token="test-tok", db_mode=True
    )


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


async def test_resolve_page_uuids_empty_input(client, mock_call):
    result = await client.resolve_page_uuids([])
    assert result == {}
    mock_call.assert_not_awaited()


async def test_resolve_page_uuids_uses_single_datascript_query():
    client = LogseqClient(LogseqConfig(endpoint="http://x/api", token="t"))
    with patch.object(client, "datascript_query", new_callable=AsyncMock) as ds:
        ds.return_value = [["uuid-a", "Page A"], ["uuid-b", "Page B"]]
        result = await client.resolve_page_uuids(["uuid-a", "uuid-b"])
        ds.assert_awaited_once()
        assert result == {"uuid-a": "Page A", "uuid-b": "Page B"}


async def test_resolve_page_uuids_empty_input_returns_empty_dict():
    client = LogseqClient(LogseqConfig(endpoint="http://x/api", token="t"))
    with patch.object(client, "datascript_query", new_callable=AsyncMock) as ds:
        result = await client.resolve_page_uuids([])
        assert result == {}
        ds.assert_not_awaited()


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


async def test_resolve_property_ident_query_binds_ident():
    client = LogseqClient(LogseqConfig(endpoint="http://x/api", token="t"))
    with patch.object(client, "datascript_query", new_callable=AsyncMock) as ds:
        ds.return_value = [[":user.property/status"]]
        result = await client.resolve_property_ident("status")
        ds.assert_awaited_once()
        query = ds.call_args.args[0]
        assert ":find ?ident" in query
        assert ":db/ident ?ident" in query
        assert '"status"' in query
        assert result == ":user.property/status"


async def test_resolve_property_ident_escapes_backslash_and_quote():
    client = LogseqClient(LogseqConfig(endpoint="http://x/api", token="t"))
    with patch.object(client, "datascript_query", new_callable=AsyncMock) as ds:
        ds.return_value = []
        await client.resolve_property_ident('bad"name\\here')
        query = ds.call_args.args[0]
        assert '\\"' in query
        assert "\\\\" in query


async def test_resolve_property_ident_returns_none_on_empty():
    client = LogseqClient(LogseqConfig(endpoint="http://x/api", token="t"))
    with patch.object(client, "datascript_query", new_callable=AsyncMock) as ds:
        ds.return_value = []
        assert await client.resolve_property_ident("unknown") is None
