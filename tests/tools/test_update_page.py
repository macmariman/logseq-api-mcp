"""Tests for update_page tool."""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.update_page import _run

_cfg = LogseqConfig("http://x", "t")
_page_result = {"id": 1, "uuid": "page-uuid", "originalName": "My Page"}

_EXISTING_BLOCK = {
    "id": 10, "uuid": "existing-block-uuid", "content": "old content",
    "level": 1, "properties": {}, "children": [],
}


class TestUpdatePage:
    async def test_update_page_append_mode(self):
        client = FakeLogseqClient({
            "get_page": _page_result,
            "get_page_blocks_tree": [_EXISTING_BLOCK],
            "append_block_in_page": {"uuid": "new-uuid"},
        })
        result = await _run(client, _cfg, "My Page", content="- New block", mode="append")
        assert "UPDATE" in result[0].text.upper()
        assert any(c[0] == "append_block_in_page" for c in client.calls)

    async def test_update_page_replace_mode_clears_first(self):
        client = FakeLogseqClient({
            "get_page": _page_result,
            "get_page_blocks_tree": [_EXISTING_BLOCK],
        })
        result = await _run(client, _cfg, "My Page", content="- Fresh block", mode="replace")
        assert any(c[0] == "delete_block" for c in client.calls)

    async def test_update_page_properties_only(self):
        client = FakeLogseqClient({
            "get_page": _page_result,
            "get_page_blocks_tree": [],
        })
        result = await _run(client, _cfg, "My Page", properties={"status": "done"})
        assert any(c[0] == "set_page_properties" for c in client.calls)
        assert "My Page" in result[0].text

    async def test_update_page_empty_content_and_properties_returns_error(self):
        client = FakeLogseqClient({"get_page": _page_result, "get_page_blocks_tree": []})
        result = await _run(client, _cfg, "My Page", content=None, properties=None)
        assert "❌" in result[0].text

    async def test_update_page_frontmatter_merged(self):
        md = "---\nstatus: active\n---\n- block content"
        captured = {}

        class CapturingClient(FakeLogseqClient):
            async def set_page_properties(self, page_name, properties):
                captured["properties"] = properties

        client = CapturingClient({
            "get_page": _page_result,
            "get_page_blocks_tree": [],
            "append_block_in_page": {"uuid": "u"},
        })
        await _run(client, _cfg, "My Page", content=md)
        assert captured.get("properties", {}).get("status") == "active"

    async def test_update_page_not_found_returns_error(self):
        client = FakeLogseqClient({"get_page": None, "get_page_blocks_tree": []})
        result = await _run(client, _cfg, "Missing Page", content="- x")
        assert "❌" in result[0].text

    async def test_update_page_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_page(self, name):
                raise RuntimeError("network error")

        result = await _run(ErrorClient(), _cfg, "My Page", content="- x")
        assert "❌ Error updating page" in result[0].text
