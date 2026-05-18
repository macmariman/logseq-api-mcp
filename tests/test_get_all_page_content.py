"""Tests for get_all_page_content tool."""

from tests.conftest import FakeLogseqClient
from src.tools.get_all_page_content import _run


class TestGetAllPageContent:
    async def test_returns_page_content(self, sample_page_data, sample_block_data):
        client = FakeLogseqClient({
            "get_page": sample_page_data,
            "get_page_blocks_tree": [sample_block_data],
        })
        result = await _run(client, "Test Page")
        assert len(result) == 1
        assert "PAGE CONTENT" in result[0].text
        assert "Test Page" in result[0].text

    async def test_page_not_found(self):
        client = FakeLogseqClient({"get_page": None, "get_page_blocks_tree": []})
        result = await _run(client, "Missing Page")
        assert "not found" in result[0].text

    async def test_block_content_included(self, sample_page_data, sample_block_data):
        client = FakeLogseqClient({
            "get_page": sample_page_data,
            "get_page_blocks_tree": [sample_block_data],
        })
        result = await _run(client, "Test Page")
        assert "Test block content" in result[0].text

    async def test_empty_blocks_shows_no_content(self, sample_page_data):
        client = FakeLogseqClient({
            "get_page": sample_page_data,
            "get_page_blocks_tree": [],
        })
        result = await _run(client, "Test Page")
        assert "[No content]" in result[0].text

    async def test_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_page(self, page_name):
                raise RuntimeError("connection refused")

        result = await _run(ErrorClient(), "My Page")
        assert "❌ Error fetching page content" in result[0].text
