"""Tests for delete_block tool."""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.delete_block import _run

_cfg = LogseqConfig("http://x", "t")
_block = {
    "id": 1,
    "uuid": "block-abc",
    "content": "some content",
    "level": 1,
    "properties": {},
    "children": [],
}


class TestDeleteBlock:
    async def test_delete_block_success(self):
        client = FakeLogseqClient({"get_block": _block})
        result = await _run(client, _cfg, "block-abc")
        assert any(c[0] == "delete_block" for c in client.calls)
        assert "✅" in result[0].text

    async def test_delete_block_shows_uuid_in_message(self):
        client = FakeLogseqClient({"get_block": _block})
        result = await _run(client, _cfg, "block-abc")
        assert "block-abc" in result[0].text

    async def test_delete_block_not_found_returns_error(self):
        client = FakeLogseqClient({"get_block": None})
        result = await _run(client, _cfg, "missing-uuid")
        assert "❌" in result[0].text
        assert not any(c[0] == "delete_block" for c in client.calls)

    async def test_delete_block_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_block(self, uuid, include_children=True):
                raise RuntimeError("connection lost")

        result = await _run(ErrorClient(), _cfg, "block-xyz")
        assert "❌ Error deleting block" in result[0].text

    async def test_delete_block_calls_client_with_correct_uuid(self):
        client = FakeLogseqClient({"get_block": _block})
        await _run(client, _cfg, "block-abc")
        delete_calls = [c for c in client.calls if c[0] == "delete_block"]
        assert len(delete_calls) == 1
        assert delete_calls[0][1][0] == "block-abc"
