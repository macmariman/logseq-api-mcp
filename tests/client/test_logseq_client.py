"""Tests for LogseqClient — all HTTP via patched _call, no real network."""

import asyncio

import aiohttp
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.client.config import LogseqConfig
from src.client.exceptions import (
    LogseqAPIError,
    LogseqAuthError,
    LogseqConnectionError,
    LogseqNotFoundError,
)
from src.client.logseq_client import LogseqClient


@pytest.fixture
def config():
    return LogseqConfig(endpoint="http://localhost:12315/api", token="test-tok")


@pytest.fixture
def client(config):
    return LogseqClient(config)


@pytest.fixture
def mock_call(client):
    with patch.object(client, "_call", new_callable=AsyncMock) as mock:
        yield mock


# ── get_all_pages ────────────────────────────────────────────────────────────


async def test_get_all_pages_calls_correct_method(client, mock_call):
    mock_call.return_value = [{"id": 1, "name": "Test"}]
    result = await client.get_all_pages()
    mock_call.assert_awaited_once_with("logseq.Editor.getAllPages")
    assert result[0]["name"] == "Test"


async def test_get_all_pages_returns_empty_list_on_none(client, mock_call):
    mock_call.return_value = None
    result = await client.get_all_pages()
    assert result == []


# ── get_page ─────────────────────────────────────────────────────────────────


async def test_get_page_calls_correct_method(client, mock_call):
    mock_call.return_value = {"id": 1, "name": "My Page"}
    result = await client.get_page("My Page")
    mock_call.assert_awaited_once_with("logseq.Editor.getPage", ["My Page"])
    assert result["name"] == "My Page"


async def test_get_page_returns_none_on_none_response(client, mock_call):
    mock_call.return_value = None
    result = await client.get_page("Missing Page")
    assert result is None


# ── get_page_blocks_tree ──────────────────────────────────────────────────────


async def test_get_page_blocks_tree(client, mock_call):
    mock_call.return_value = [{"content": "Block 1"}]
    result = await client.get_page_blocks_tree("My Page")
    mock_call.assert_awaited_once_with("logseq.Editor.getPageBlocksTree", ["My Page"])
    assert result[0]["content"] == "Block 1"


async def test_get_page_blocks_tree_returns_empty_on_none(client, mock_call):
    mock_call.return_value = None
    result = await client.get_page_blocks_tree("Missing")
    assert result == []


# ── delete_page ───────────────────────────────────────────────────────────────


async def test_delete_page_calls_correct_method(client, mock_call):
    mock_call.return_value = True
    await client.delete_page("My Page")
    mock_call.assert_awaited_once_with("logseq.Editor.deletePage", ["My Page"])


# ── rename_page ───────────────────────────────────────────────────────────────


async def test_rename_page_calls_correct_method(client, mock_call):
    mock_call.return_value = True
    await client.rename_page("Old Name", "New Name")
    mock_call.assert_awaited_once_with(
        "logseq.Editor.renamePage", ["Old Name", "New Name"]
    )


# ── search ────────────────────────────────────────────────────────────────────


async def test_search_with_no_options(client, mock_call):
    mock_call.return_value = {"blocks": []}
    await client.search("test query")
    mock_call.assert_awaited_once_with("logseq.App.search", ["test query", {}])


async def test_search_passes_options(client, mock_call):
    mock_call.return_value = {"blocks": []}
    await client.search("test", {"limit": 10})
    mock_call.assert_awaited_once_with("logseq.App.search", ["test", {"limit": 10}])


async def test_search_returns_empty_dict_on_none(client, mock_call):
    mock_call.return_value = None
    result = await client.search("test")
    assert result == {}


# ── query_dsl ─────────────────────────────────────────────────────────────────


async def test_query_dsl_calls_correct_method(client, mock_call):
    mock_call.return_value = [{"name": "Page A"}]
    result = await client.query_dsl("(page-property status active)")
    mock_call.assert_awaited_once_with("logseq.DB.q", ["(page-property status active)"])
    assert result[0]["name"] == "Page A"


async def test_query_dsl_returns_empty_list_on_none(client, mock_call):
    mock_call.return_value = None
    result = await client.query_dsl("(anything)")
    assert result == []


# ── update_block ──────────────────────────────────────────────────────────────


async def test_update_block_calls_correct_method(client, mock_call):
    mock_call.return_value = None
    await client.update_block("uuid-123", "new content")
    mock_call.assert_awaited_once_with(
        "logseq.Editor.updateBlock", ["uuid-123", "new content"]
    )


# ── delete_block ──────────────────────────────────────────────────────────────


async def test_delete_block_calls_correct_method(client, mock_call):
    mock_call.return_value = None
    await client.delete_block("uuid-456")
    mock_call.assert_awaited_once_with("logseq.Editor.removeBlock", ["uuid-456"])


# ── append_block_in_page ──────────────────────────────────────────────────────


async def test_append_block_in_page_calls_correct_method(client, mock_call):
    mock_call.return_value = {"uuid": "new-uuid"}
    result = await client.append_block_in_page("My Page", "content")
    mock_call.assert_awaited_once_with(
        "logseq.Editor.appendBlockInPage", ["My Page", "content"]
    )
    assert result["uuid"] == "new-uuid"


# ── insert_block ──────────────────────────────────────────────────────────────


async def test_insert_block_as_child(client, mock_call):
    mock_call.return_value = {"uuid": "child-uuid"}
    result = await client.insert_block("parent-uuid", "child content", sibling=False)
    call_args = mock_call.call_args
    assert call_args[0][0] == "logseq.Editor.insertBlock"
    assert call_args[0][1][1] == "child content"
    assert result["uuid"] == "child-uuid"


# ── get_block ─────────────────────────────────────────────────────────────────


async def test_get_block_with_children(client, mock_call):
    mock_call.return_value = {"uuid": "b1", "content": "text", "children": []}
    result = await client.get_block("b1", include_children=True)
    assert result["uuid"] == "b1"


async def test_get_block_returns_none_on_none(client, mock_call):
    mock_call.return_value = None
    result = await client.get_block("missing")
    assert result is None


# ── _call HTTP error handling ─────────────────────────────────────────────────


def _make_session_mock(mock_response: MagicMock):
    """Build a properly-shaped aiohttp.ClientSession mock."""
    mock_sess = MagicMock()
    mock_post_ctx = MagicMock()
    mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_sess.post.return_value = mock_post_ctx
    return mock_sess


async def test_call_raises_auth_error_on_401(config):
    client = LogseqClient(config)
    mock_response = MagicMock()
    mock_response.status = 401
    mock_response.json = AsyncMock(return_value={})

    with patch("aiohttp.ClientSession") as mock_sess_cls:
        mock_sess = _make_session_mock(mock_response)
        mock_sess_cls.return_value.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_sess_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        with pytest.raises(LogseqAuthError):
            await client._call("logseq.Editor.getAllPages")


async def test_call_raises_api_error_on_500(config):
    client = LogseqClient(config)
    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.json = AsyncMock(return_value={})
    mock_response.text = AsyncMock(return_value="server error")

    with patch("aiohttp.ClientSession") as mock_sess_cls:
        mock_sess = _make_session_mock(mock_response)
        mock_sess_cls.return_value.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_sess_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        with pytest.raises(LogseqAPIError) as exc_info:
            await client._call("logseq.Editor.getAllPages")
        assert exc_info.value.status_code == 500


# ── B2: _call HTTP error mapping (typed exceptions) ──────────────────────────


def _client():
    return LogseqClient(LogseqConfig(endpoint="http://x/api", token="t"))


def _mock_post(status: int, payload=None):
    """Return a patch context that makes the next POST return `status`."""
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=payload or {})
    resp.text = AsyncMock(return_value=str(payload or ""))
    sess = MagicMock()
    sess.post.return_value.__aenter__ = AsyncMock(return_value=resp)
    sess.post.return_value.__aexit__ = AsyncMock(return_value=None)
    ctx = patch("aiohttp.ClientSession")
    return ctx, sess, resp


async def test_call_raises_auth_on_401():
    ctx, sess, _ = _mock_post(401)
    with ctx as mock_sess_class:
        mock_sess_class.return_value.__aenter__ = AsyncMock(return_value=sess)
        mock_sess_class.return_value.__aexit__ = AsyncMock(return_value=None)
        with pytest.raises(LogseqAuthError):
            await _client()._call("logseq.Editor.getAllPages")


async def test_call_raises_not_found_on_404():
    ctx, sess, _ = _mock_post(404)
    with ctx as mock_sess_class:
        mock_sess_class.return_value.__aenter__ = AsyncMock(return_value=sess)
        mock_sess_class.return_value.__aexit__ = AsyncMock(return_value=None)
        with pytest.raises(LogseqNotFoundError):
            await _client()._call("logseq.Editor.bogusMethod")


async def test_call_raises_api_error_on_500_typed():
    ctx, sess, _ = _mock_post(500)
    with ctx as mock_sess_class:
        mock_sess_class.return_value.__aenter__ = AsyncMock(return_value=sess)
        mock_sess_class.return_value.__aexit__ = AsyncMock(return_value=None)
        with pytest.raises(LogseqAPIError) as exc_info:
            await _client()._call("logseq.Editor.getAllPages")
        assert exc_info.value.status_code == 500
        assert not isinstance(exc_info.value, (LogseqAuthError, LogseqNotFoundError))


async def test_call_raises_connection_error_on_network_failure():
    ctx = patch("aiohttp.ClientSession")
    with ctx as mock_sess_class:
        mock_sess_class.side_effect = aiohttp.ClientConnectorError(
            connection_key=MagicMock(), os_error=OSError("boom")
        )
        with pytest.raises(LogseqConnectionError):
            await _client()._call("logseq.Editor.getAllPages")


async def test_call_raises_connection_error_on_timeout():
    ctx = patch("aiohttp.ClientSession")
    with ctx as mock_sess_class:
        mock_sess_class.side_effect = asyncio.TimeoutError()
        with pytest.raises(LogseqConnectionError):
            await _client()._call("logseq.Editor.getAllPages")


async def test_create_page_sends_properties_as_second_arg():
    client = _client()
    with patch.object(client, "_call", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {"uuid": "u"}
        await client.create_page(
            "MyPage", properties={"status": "active"}, fmt="markdown"
        )
        mock_call.assert_awaited_once_with(
            "logseq.Editor.createPage",
            ["MyPage", {"status": "active"}, {"format": "markdown"}],
        )


async def test_create_page_omits_properties_when_none():
    client = _client()
    with patch.object(client, "_call", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {"uuid": "u"}
        await client.create_page("MyPage")
        mock_call.assert_awaited_once_with(
            "logseq.Editor.createPage",
            ["MyPage", {}, {}],
        )
