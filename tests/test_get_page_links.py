"""Tests for get_page_links tool."""

from tests.conftest import FakeLogseqClient
from src.tools.get_page_links import _run


class TestGetPageLinks:
    async def test_returns_analysis_when_links_found(self):
        linked_refs = [
            [{"id": 10, "name": "linking-page", "originalName": "Linking Page"}, {"uuid": "b1"}],
        ]
        all_pages = [
            {"id": 10, "uuid": "p1", "name": "linking-page", "originalName": "Linking Page",
             "journal?": False, "createdAt": 0, "updatedAt": 0},
        ]
        client = FakeLogseqClient({
            "get_page_linked_references": linked_refs,
            "get_all_pages": all_pages,
        })
        result = await _run(client, "Target Page")
        assert len(result) == 1
        assert "PAGE LINKS ANALYSIS" in result[0].text
        assert "Linking Page" in result[0].text

    async def test_no_links_returns_message(self):
        client = FakeLogseqClient({
            "get_page_linked_references": [],
            "get_all_pages": [],
        })
        result = await _run(client, "Isolated Page")
        assert "No pages link to" in result[0].text

    async def test_reference_count_shown(self):
        linked_refs = [
            [{"id": 10, "name": "pg"}, {"uuid": "b1"}, {"uuid": "b2"}, {"uuid": "b3"}],
        ]
        client = FakeLogseqClient({
            "get_page_linked_references": linked_refs,
            "get_all_pages": [{"id": 10, "uuid": "x", "name": "pg", "originalName": "Pg",
                               "journal?": False, "createdAt": 0, "updatedAt": 0}],
        })
        result = await _run(client, "Target")
        assert "References: 3" in result[0].text

    async def test_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_page_linked_references(self, page_name):
                raise RuntimeError("boom")

        result = await _run(ErrorClient(), "Target")
        assert "❌ Error fetching page links: boom" in result[0].text
