"""Tests for get_block_content tool."""

import json

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.get_block_content import _run

_cfg = LogseqConfig("http://x", "t")
_cfg_db = LogseqConfig("http://x", "t", db_mode=True)


class TestGetBlockContent:
    # ── basic behaviour ───────────────────────────────────────────────────────

    async def test_returns_block_detail(self, sample_block_data):
        client = FakeLogseqClient({"get_block": sample_block_data})
        result = await _run(client, _cfg, "block-uuid-456")
        assert "block-uuid-456" in result[0].text
        assert "Test block content" in result[0].text

    async def test_block_not_found(self):
        client = FakeLogseqClient({"get_block": None})
        result = await _run(client, _cfg, "missing-uuid")
        assert "not found" in result[0].text

    async def test_block_properties_shown(self, sample_block_data):
        client = FakeLogseqClient({"get_block": sample_block_data})
        result = await _run(client, _cfg, "block-uuid-456")
        assert "status" in result[0].text
        assert "active" in result[0].text

    async def test_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_block(self, block_uuid, include_children=True):
                raise RuntimeError("timeout")

        result = await _run(ErrorClient(), _cfg, "some-uuid")
        assert "❌ Error fetching block content: timeout" in result[0].text

    # ── format parameter ──────────────────────────────────────────────────────

    async def test_format_text_returns_readable_text(self, sample_block_data):
        client = FakeLogseqClient({"get_block": sample_block_data})
        result = await _run(client, _cfg, "block-uuid-456", fmt="text")
        assert "Block" in result[0].text

    async def test_format_json_returns_valid_json(self, sample_block_data):
        client = FakeLogseqClient({"get_block": sample_block_data})
        result = await _run(client, _cfg, "block-uuid-456", fmt="json")
        data = json.loads(result[0].text)
        assert "uuid" in data
        assert "content" in data

    async def test_format_json_uuid_matches(self, sample_block_data):
        client = FakeLogseqClient({"get_block": sample_block_data})
        result = await _run(client, _cfg, "block-uuid-456", fmt="json")
        data = json.loads(result[0].text)
        assert data["uuid"] == "block-uuid-456"

    # ── include_children parameter ────────────────────────────────────────────

    async def test_include_children_true_fetches_with_children(self, sample_block_data):
        client = FakeLogseqClient({"get_block": sample_block_data})
        await _run(client, _cfg, "block-uuid-456", include_children=True)
        call = next(c for c in client.calls if c[0] == "get_block")
        assert call[2]["include_children"] is True

    async def test_include_children_false_fetches_without_children(
        self, sample_block_data
    ):
        client = FakeLogseqClient({"get_block": sample_block_data})
        await _run(client, _cfg, "block-uuid-456", include_children=False)
        call = next(c for c in client.calls if c[0] == "get_block")
        assert call[2]["include_children"] is False

    # ── db_mode property injection ────────────────────────────────────────────

    async def test_db_mode_calls_get_blocks_db_properties(self, sample_block_data):
        client = FakeLogseqClient(
            {
                "get_block": sample_block_data,
                "get_blocks_db_properties": {"block-uuid-456": {"priority": "A"}},
            }
        )
        await _run(client, _cfg_db, "block-uuid-456")
        assert any(c[0] == "get_blocks_db_properties" for c in client.calls)

    async def test_db_mode_properties_shown_in_output(self, sample_block_data):
        client = FakeLogseqClient(
            {
                "get_block": sample_block_data,
                "get_blocks_db_properties": {"block-uuid-456": {"priority": "A"}},
            }
        )
        result = await _run(client, _cfg_db, "block-uuid-456")
        assert "priority" in result[0].text

    async def test_non_db_mode_skips_db_properties(self, sample_block_data):
        client = FakeLogseqClient({"get_block": sample_block_data})
        await _run(client, _cfg, "block-uuid-456")
        assert not any(c[0] == "get_blocks_db_properties" for c in client.calls)
