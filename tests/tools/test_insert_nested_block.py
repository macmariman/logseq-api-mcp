"""Tests for insert_nested_block tool."""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.insert_nested_block import _run

_cfg = LogseqConfig("http://x", "t")
_parent = {
    "id": 1,
    "uuid": "parent-uuid",
    "content": "parent block",
    "level": 1,
    "properties": {},
    "children": [],
}
_new_block = {"uuid": "new-child-uuid"}


class TestInsertNestedBlock:
    async def test_insert_as_child_default(self):
        client = FakeLogseqClient(
            {
                "get_block": _parent,
                "insert_block": _new_block,
            }
        )
        await _run(client, _cfg, "parent-uuid", "child content")
        insert_calls = [c for c in client.calls if c[0] == "insert_block"]
        assert len(insert_calls) == 1
        assert insert_calls[0][2]["sibling"] is False

    async def test_insert_as_sibling_when_sibling_true(self):
        client = FakeLogseqClient(
            {
                "get_block": _parent,
                "insert_block": _new_block,
            }
        )
        await _run(client, _cfg, "parent-uuid", "sibling content", sibling=True)
        insert_calls = [c for c in client.calls if c[0] == "insert_block"]
        assert insert_calls[0][2]["sibling"] is True

    async def test_insert_with_properties(self):
        client = FakeLogseqClient(
            {
                "get_block": _parent,
                "insert_block": _new_block,
            }
        )
        result = await _run(
            client, _cfg, "parent-uuid", "content", properties={"status": "todo"}
        )
        assert "✅" in result[0].text

    async def test_insert_returns_new_block_uuid(self):
        client = FakeLogseqClient(
            {
                "get_block": _parent,
                "insert_block": _new_block,
            }
        )
        result = await _run(client, _cfg, "parent-uuid", "content")
        assert "new-child-uuid" in result[0].text

    async def test_insert_parent_not_found_returns_error(self):
        client = FakeLogseqClient({"get_block": None})
        result = await _run(client, _cfg, "ghost-uuid", "content")
        assert "❌" in result[0].text
        assert not any(c[0] == "insert_block" for c in client.calls)

    async def test_insert_empty_content_is_error(self):
        client = FakeLogseqClient({"get_block": _parent})
        result = await _run(client, _cfg, "parent-uuid", "")
        assert "❌" in result[0].text

    async def test_insert_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_block(self, uuid, include_children=True):
                raise RuntimeError("API error")

        result = await _run(ErrorClient(), _cfg, "parent-uuid", "content")
        assert "❌ Error inserting block" in result[0].text
