"""Tests for search tool."""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.search import _run

_cfg = LogseqConfig("http://x", "t")
_cfg_db = LogseqConfig("http://x", "t", db_mode=True)
_cfg_excl = LogseqConfig("http://x", "t", exclude_tags=("private",))

_SEARCH_RESULT = {
    "blocks": [{"block/content": "matching block content", "uuid": "b1", "page": 1}],
    "pages": ["Public Page", "Another Page"],
    "pages-content": [
        {"block/snippet": "snippet of Public Page"},
    ],
    "files": [],
}


class TestSearch:
    async def test_search_returns_blocks(self):
        client = FakeLogseqClient({"search": _SEARCH_RESULT, "get_all_pages": []})
        result = await _run(client, _cfg, "matching")
        assert "matching block content" in result[0].text

    async def test_search_returns_pages(self):
        client = FakeLogseqClient({"search": _SEARCH_RESULT, "get_all_pages": []})
        result = await _run(client, _cfg, "page")
        assert "Public Page" in result[0].text

    async def test_search_no_results(self):
        empty = {"blocks": [], "pages": [], "pages-content": [], "files": []}
        client = FakeLogseqClient({"search": empty, "get_all_pages": []})
        result = await _run(client, _cfg, "nothing")
        assert "Total results: 0" in result[0].text

    async def test_search_excludes_restricted_pages(self):
        pages = [
            {
                "id": 1,
                "uuid": "p1",
                "name": "secret",
                "originalName": "Secret",
                "journal?": False,
                "createdAt": 0,
                "updatedAt": 0,
                "properties": {"tags": ["private"]},
            },
        ]
        search_result = {
            "blocks": [],
            "pages": ["Secret", "Safe Page"],
            "pages-content": [],
            "files": [],
        }
        client = FakeLogseqClient({"search": search_result, "get_all_pages": pages})
        result = await _run(client, _cfg_excl, "query")
        assert "Safe Page" in result[0].text
        assert "Secret" not in result[0].text

    async def test_search_db_mode_uses_different_formatter(self):
        db_result = {
            "blocks": [
                {"page?": True, "fullTitle": "DB Page", "uuid": "p1"},
                {
                    "page?": False,
                    "content": "DB block content",
                    "uuid": "b1",
                    "page": "p1",
                },
            ],
            "files": [],
        }
        client = FakeLogseqClient({"search": db_result, "get_all_pages": []})
        result = await _run(client, _cfg_db, "query")
        assert "DB Page" in result[0].text
        assert "DB block content" in result[0].text

    async def test_search_limit_respected(self):
        blocks = [
            {"block/content": f"block {i}", "uuid": f"b{i}", "page": 1}
            for i in range(50)
        ]
        search_result = {
            "blocks": blocks,
            "pages": [],
            "pages-content": [],
            "files": [],
        }
        client = FakeLogseqClient({"search": search_result, "get_all_pages": []})
        result = await _run(client, _cfg, "block", limit=5)
        text = result[0].text
        assert "block 0" in text
        assert "block 49" not in text

    async def test_search_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def search(self, query, options=None):
                raise RuntimeError("connection failed")

        result = await _run(ErrorClient(), _cfg, "query")
        assert "❌ Error searching" in result[0].text
