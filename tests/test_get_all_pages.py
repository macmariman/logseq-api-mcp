"""Tests for get_all_pages tool."""

import pytest
from tests.conftest import FakeLogseqClient
from src.tools.get_all_pages import _run


class TestGetAllPages:
    """Test cases for get_all_pages._run()."""

    async def test_get_all_pages_success(self, sample_page_data):
        client = FakeLogseqClient({"get_all_pages": [sample_page_data]})
        result = await _run(client)
        assert len(result) == 1
        assert "📊 **LOGSEQ PAGES LISTING**" in result[0].text
        assert "Test Page" in result[0].text

    async def test_get_all_pages_with_limits(self, sample_page_data):
        pages = [
            {**sample_page_data, "id": i, "originalName": f"Page {i}"}
            for i in range(10)
        ]
        client = FakeLogseqClient({"get_all_pages": pages})
        result = await _run(client, start=0, end=3)
        assert len(result) == 1
        assert "showing indices 0-3" in result[0].text

    async def test_get_all_pages_empty(self):
        client = FakeLogseqClient({"get_all_pages": []})
        result = await _run(client)
        assert len(result) == 1
        assert "No pages found in Logseq graph" in result[0].text

    async def test_get_all_pages_separates_journals(self):
        pages = [
            {"id": 1, "uuid": "a", "originalName": "Regular", "journal?": False, "createdAt": 0, "updatedAt": 0},
            {"id": 2, "uuid": "b", "originalName": "2024-01-01", "journal?": True, "createdAt": 0, "updatedAt": 0},
        ]
        client = FakeLogseqClient({"get_all_pages": pages})
        result = await _run(client)
        assert "REGULAR PAGES" in result[0].text
        assert "JOURNAL PAGES" in result[0].text

    async def test_get_all_pages_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_all_pages(self):
                raise RuntimeError("Network error")

        result = await _run(ErrorClient())
        assert len(result) == 1
        assert "❌ Error fetching pages: Network error" in result[0].text
