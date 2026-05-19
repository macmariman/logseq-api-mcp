"""Tests for query tool."""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.query import query as _run

_cfg = LogseqConfig("http://x", "t")
_cfg_excl = LogseqConfig("http://x", "t", exclude_tags=("private",))

_PAGE_RESULT = {
    "originalName": "My Page",
    "name": "my-page",
    "uuid": "p1",
    "journal?": False,
}
_BLOCK_RESULT = {
    "content": "block content",
    "uuid": "b2",
    "page": {"name": "other", "originalName": "Other"},
}


class TestQuery:
    async def test_query_returns_pages(self):
        client = FakeLogseqClient({"query_dsl": [_PAGE_RESULT]})
        result = await _run(client, _cfg, "[:find ?p :where [?p :page/name]]")
        assert "My Page" in result[0].text or "my-page" in result[0].text

    async def test_query_filter_pages_only(self):
        items = [_PAGE_RESULT, _BLOCK_RESULT]
        client = FakeLogseqClient({"query_dsl": items})
        result = await _run(client, _cfg, "query", result_type="pages_only")
        assert "My Page" in result[0].text or "my-page" in result[0].text

    async def test_query_filter_blocks_only(self):
        items = [_PAGE_RESULT, _BLOCK_RESULT]
        client = FakeLogseqClient({"query_dsl": items})
        result = await _run(client, _cfg, "query", result_type="blocks_only")
        assert "block content" in result[0].text

    async def test_query_applies_exclude_tags(self):
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
        items = [
            {
                "page": {"name": "secret", "originalName": "Secret"},
                "content": "x",
                "uuid": "b1",
            }
        ]
        client = FakeLogseqClient({"query_dsl": items, "get_all_pages": pages})
        result = await _run(client, _cfg_excl, "query")
        assert "Secret" not in result[0].text

    async def test_query_empty_result(self):
        client = FakeLogseqClient({"query_dsl": []})
        result = await _run(client, _cfg, "empty query")
        assert "0" in result[0].text or "no results" in result[0].text.lower()

    async def test_query_limit_respected(self):
        items = [
            {"content": f"item {i}", "uuid": f"b{i}", "page": {"name": "p"}}
            for i in range(50)
        ]
        client = FakeLogseqClient({"query_dsl": items})
        result = await _run(client, _cfg, "query", limit=5)
        assert "item 0" in result[0].text
        assert "item 49" not in result[0].text

    async def test_query_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def query_dsl(self, query):
                raise RuntimeError("bad query")

        result = await _run(ErrorClient(), _cfg, "broken")
        assert "❌ Error running query" in result[0].text
