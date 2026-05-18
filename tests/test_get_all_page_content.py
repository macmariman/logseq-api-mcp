"""Tests for get_all_page_content tool."""

import json

import pytest

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.get_all_page_content import _run


def _page(name: str) -> dict:
    return {
        "id": 1,
        "uuid": "page-uuid",
        "originalName": name,
        "name": name,
        "journal?": False,
        "createdAt": 0,
        "updatedAt": 0,
    }


def _block(content: str, children: list | None = None, uuid: str = "block-uuid") -> dict:
    return {
        "id": hash(content),
        "uuid": uuid,
        "content": content,
        "level": 1,
        "page": {"id": 1},
        "properties": {},
        "children": children or [],
    }


_cfg = LogseqConfig("http://x", "t")
_cfg_db = LogseqConfig("http://x", "t", db_mode=True)


class TestGetAllPageContent:
    # ── basic behaviour ───────────────────────────────────────────────────────

    async def test_returns_page_content(self, sample_page_data, sample_block_data):
        client = FakeLogseqClient({
            "get_page": sample_page_data,
            "get_page_blocks_tree": [sample_block_data],
        })
        result = await _run(client, _cfg, "Test Page")
        assert "PAGE CONTENT" in result[0].text
        assert "Test Page" in result[0].text

    async def test_page_not_found(self):
        client = FakeLogseqClient({"get_page": None, "get_page_blocks_tree": []})
        result = await _run(client, _cfg, "Missing Page")
        assert "not found" in result[0].text

    async def test_block_content_included(self, sample_page_data, sample_block_data):
        client = FakeLogseqClient({
            "get_page": sample_page_data,
            "get_page_blocks_tree": [sample_block_data],
        })
        result = await _run(client, _cfg, "Test Page")
        assert "Test block content" in result[0].text

    async def test_empty_blocks_shows_no_content(self, sample_page_data):
        client = FakeLogseqClient({
            "get_page": sample_page_data,
            "get_page_blocks_tree": [],
        })
        result = await _run(client, _cfg, "Test Page")
        assert "[No content]" in result[0].text

    async def test_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_page(self, page_name):
                raise RuntimeError("connection refused")

        result = await _run(ErrorClient(), _cfg, "My Page")
        assert "❌ Error fetching page content" in result[0].text

    # ── format parameter ──────────────────────────────────────────────────────

    async def test_format_text_default_returns_text(self, sample_page_data, sample_block_data):
        client = FakeLogseqClient({
            "get_page": sample_page_data,
            "get_page_blocks_tree": [sample_block_data],
        })
        result = await _run(client, _cfg, "Test Page", fmt="text")
        assert "PAGE CONTENT" in result[0].text

    async def test_format_json_returns_valid_json(self, sample_page_data, sample_block_data):
        client = FakeLogseqClient({
            "get_page": sample_page_data,
            "get_page_blocks_tree": [sample_block_data],
        })
        result = await _run(client, _cfg, "Test Page", fmt="json")
        data = json.loads(result[0].text)
        assert "page" in data
        assert "blocks" in data

    async def test_format_json_contains_page_name(self, sample_page_data, sample_block_data):
        client = FakeLogseqClient({
            "get_page": sample_page_data,
            "get_page_blocks_tree": [sample_block_data],
        })
        result = await _run(client, _cfg, "Test Page", fmt="json")
        data = json.loads(result[0].text)
        assert data["page"]["name"] == "Test Page"

    # ── max_depth parameter ───────────────────────────────────────────────────

    async def test_max_depth_unlimited_shows_all_levels(self, sample_page_data):
        deep = _block("root", children=[_block("child", children=[_block("grandchild")])])
        client = FakeLogseqClient({
            "get_page": sample_page_data,
            "get_page_blocks_tree": [deep],
        })
        result = await _run(client, _cfg, "Test Page", max_depth=-1)
        assert "grandchild" in result[0].text

    async def test_max_depth_zero_shows_only_root(self, sample_page_data):
        deep = _block("root", children=[_block("child", children=[_block("grandchild")])])
        client = FakeLogseqClient({
            "get_page": sample_page_data,
            "get_page_blocks_tree": [deep],
        })
        result = await _run(client, _cfg, "Test Page", max_depth=0)
        assert "root" in result[0].text
        assert "grandchild" not in result[0].text

    async def test_max_depth_one_shows_root_and_child(self, sample_page_data):
        deep = _block("root", children=[_block("child", children=[_block("grandchild")])])
        client = FakeLogseqClient({
            "get_page": sample_page_data,
            "get_page_blocks_tree": [deep],
        })
        result = await _run(client, _cfg, "Test Page", max_depth=1)
        assert "child" in result[0].text
        assert "grandchild" not in result[0].text

    # ── resolve_refs parameter ────────────────────────────────────────────────

    async def test_resolve_refs_db_mode_calls_resolve_page_uuids(self, sample_page_data):
        _uuid = "12345678-1234-1234-1234-123456789012"
        block = _block(f"[[{_uuid}]]", uuid="b1")
        client = FakeLogseqClient({
            "get_page": sample_page_data,
            "get_page_blocks_tree": [block],
            "resolve_page_uuids": {_uuid: "Referenced Page"},
        })
        result = await _run(client, _cfg_db, "Test Page", resolve_refs=True)
        assert any(c[0] == "resolve_page_uuids" for c in client.calls)

    async def test_resolve_refs_false_skips_uuid_resolution(self, sample_page_data):
        block = _block("((ref-uuid))", uuid="b1")
        client = FakeLogseqClient({
            "get_page": sample_page_data,
            "get_page_blocks_tree": [block],
        })
        result = await _run(client, _cfg_db, "Test Page", resolve_refs=False)
        assert not any(c[0] == "resolve_page_uuids" for c in client.calls)

    async def test_resolve_refs_non_db_mode_skips_resolution(self, sample_page_data):
        block = _block("((ref-uuid))", uuid="b1")
        client = FakeLogseqClient({
            "get_page": sample_page_data,
            "get_page_blocks_tree": [block],
        })
        result = await _run(client, _cfg, "Test Page", resolve_refs=True)
        assert not any(c[0] == "resolve_page_uuids" for c in client.calls)
