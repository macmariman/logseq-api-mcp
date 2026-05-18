"""Tests for get_block_content tool."""

from tests.conftest import FakeLogseqClient
from src.tools.get_block_content import _run


class TestGetBlockContent:
    async def test_returns_block_detail(self, sample_block_data):
        client = FakeLogseqClient({"get_block": sample_block_data})
        result = await _run(client, "block-uuid-456")
        assert len(result) == 1
        assert "block-uuid-456" in result[0].text
        assert "Test block content" in result[0].text

    async def test_block_not_found(self):
        client = FakeLogseqClient({"get_block": None})
        result = await _run(client, "missing-uuid")
        assert "not found" in result[0].text

    async def test_block_properties_shown(self, sample_block_data):
        client = FakeLogseqClient({"get_block": sample_block_data})
        result = await _run(client, "block-uuid-456")
        assert "status" in result[0].text
        assert "active" in result[0].text

    async def test_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_block(self, block_uuid, include_children=True):
                raise RuntimeError("timeout")

        result = await _run(ErrorClient(), "some-uuid")
        assert "❌ Error fetching block content: timeout" in result[0].text
