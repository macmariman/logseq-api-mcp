"""Tests for get_page_links backward-compat alias."""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.get_page_links import get_page_links as _run

_cfg = LogseqConfig("http://x", "t")

_LINKING_PAGE = {
    "id": 10,
    "uuid": "p1",
    "name": "linking-page",
    "originalName": "Linking Page",
    "journal?": False,
    "createdAt": 0,
    "updatedAt": 0,
}


class TestGetPageLinks:
    async def test_returns_analysis_when_links_found(self):
        linked_refs = [
            [
                {"id": 10, "name": "linking-page", "originalName": "Linking Page"},
                {"uuid": "b1", "content": "ref"},
            ],
        ]
        client = FakeLogseqClient(
            {
                "get_page_linked_references": linked_refs,
                "get_all_pages": [_LINKING_PAGE],
            }
        )
        result = await _run(client, _cfg, "Target Page")
        assert "PAGE BACKLINKS" in result[0].text
        assert "Linking Page" in result[0].text

    async def test_no_links_returns_message(self):
        client = FakeLogseqClient(
            {
                "get_page_linked_references": [],
                "get_all_pages": [],
            }
        )
        result = await _run(client, _cfg, "Isolated Page")
        assert "No pages link to" in result[0].text

    async def test_reference_count_shown(self):
        linked_refs = [
            [
                {"id": 10, "name": "pg"},
                {"uuid": "b1", "content": "x"},
                {"uuid": "b2", "content": "y"},
                {"uuid": "b3", "content": "z"},
            ],
        ]
        client = FakeLogseqClient(
            {
                "get_page_linked_references": linked_refs,
                "get_all_pages": [
                    {
                        "id": 10,
                        "uuid": "x",
                        "name": "pg",
                        "originalName": "Pg",
                        "journal?": False,
                        "createdAt": 0,
                        "updatedAt": 0,
                    }
                ],
            }
        )
        result = await _run(client, _cfg, "Target")
        assert "References: 3" in result[0].text

    async def test_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_page_linked_references(self, page_name):
                raise RuntimeError("boom")

        result = await _run(ErrorClient(), _cfg, "Target")
        assert "❌ Error fetching page backlinks: boom" in result[0].text
