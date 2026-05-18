"""Tests for update_block tool."""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.update_block import _run

_cfg = LogseqConfig("http://x", "t")
_block = {"id": 1, "uuid": "block-xyz", "content": "old text", "level": 1,
           "properties": {}, "children": []}


class TestUpdateBlock:
    async def test_update_block_success(self):
        client = FakeLogseqClient({"get_block": _block})
        result = await _run(client, _cfg, "block-xyz", "new text")
        assert any(c[0] == "update_block" for c in client.calls)
        assert "✅" in result[0].text

    async def test_update_block_returns_uuid_in_message(self):
        client = FakeLogseqClient({"get_block": _block})
        result = await _run(client, _cfg, "block-xyz", "new text")
        assert "block-xyz" in result[0].text

    async def test_update_block_empty_content_is_error(self):
        client = FakeLogseqClient({"get_block": _block})
        result = await _run(client, _cfg, "block-xyz", "")
        assert "❌" in result[0].text
        assert not any(c[0] == "update_block" for c in client.calls)

    async def test_update_block_whitespace_content_is_error(self):
        client = FakeLogseqClient({"get_block": _block})
        result = await _run(client, _cfg, "block-xyz", "   \n  ")
        assert "❌" in result[0].text

    async def test_update_block_not_found_returns_error(self):
        client = FakeLogseqClient({"get_block": None})
        result = await _run(client, _cfg, "missing", "new content")
        assert "❌" in result[0].text
        assert not any(c[0] == "update_block" for c in client.calls)

    async def test_update_block_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_block(self, uuid, include_children=True):
                raise RuntimeError("network issue")

        result = await _run(ErrorClient(), _cfg, "block-xyz", "text")
        assert "❌ Error updating block" in result[0].text

    async def test_update_block_passes_content_to_client(self):
        client = FakeLogseqClient({"get_block": _block})
        await _run(client, _cfg, "block-xyz", "updated content")
        update_calls = [c for c in client.calls if c[0] == "update_block"]
        assert update_calls[0][1] == ("block-xyz", "updated content")
