"""Tests for set_block_properties tool."""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.set_block_properties import set_block_properties as _run

_cfg = LogseqConfig("http://x", "t")
_cfg_db = LogseqConfig("http://x", "t", db_mode=True)
_block = {
    "id": 1,
    "uuid": "block-prop",
    "content": "text",
    "level": 1,
    "properties": {},
    "children": [],
}


class TestSetBlockProperties:
    async def test_set_block_properties_requires_db_mode(self):
        """Non-DB mode returns an error — this tool is DB-mode only."""
        client = FakeLogseqClient({"get_block": _block})
        result = await _run(client, _cfg, "block-prop", {"status": "done"})
        assert "❌" in result[0].text
        assert "db" in result[0].text.lower() or "mode" in result[0].text.lower()

    async def test_set_block_properties_calls_upsert_for_each_property(self):
        client = FakeLogseqClient({"get_block": _block})
        await _run(client, _cfg_db, "block-prop", {"status": "done", "priority": "A"})
        upsert_calls = [c for c in client.calls if c[0] == "upsert_block_property"]
        assert len(upsert_calls) == 2

    async def test_set_block_properties_success_message(self):
        client = FakeLogseqClient({"get_block": _block})
        result = await _run(client, _cfg_db, "block-prop", {"status": "done"})
        assert "✅" in result[0].text
        assert "block-prop" in result[0].text

    async def test_set_block_properties_not_found_returns_error(self):
        client = FakeLogseqClient({"get_block": None})
        result = await _run(client, _cfg_db, "ghost-block", {"key": "val"})
        assert "❌" in result[0].text
        assert not any(c[0] == "upsert_block_property" for c in client.calls)

    async def test_set_block_properties_empty_dict_is_error(self):
        client = FakeLogseqClient({"get_block": _block})
        result = await _run(client, _cfg_db, "block-prop", {})
        assert "❌" in result[0].text

    async def test_set_block_properties_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_block(self, uuid, include_children=True):
                raise RuntimeError("DB error")

        result = await _run(ErrorClient(), _cfg_db, "block-prop", {"k": "v"})
        assert "❌ Error setting block properties" in result[0].text
