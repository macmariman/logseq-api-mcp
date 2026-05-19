"""Tests for find_pages_by_property tool."""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.find_pages_by_property import find_pages_by_property as _run

_cfg = LogseqConfig("http://x", "t")

_STATUS_PAGE = {
    "originalName": "Task A",
    "name": "task-a",
    "uuid": "p1",
    "journal?": False,
}
_OTHER_PAGE = {
    "originalName": "Task B",
    "name": "task-b",
    "uuid": "p2",
    "journal?": False,
}


class TestFindPagesByProperty:
    async def test_find_by_property_name_only(self):
        client = FakeLogseqClient({"query_dsl": [_STATUS_PAGE, _OTHER_PAGE]})
        result = await _run(client, _cfg, "status")
        assert "Task A" in result[0].text
        assert "Task B" in result[0].text

    async def test_find_by_property_name_and_value(self):
        client = FakeLogseqClient({"query_dsl": [_STATUS_PAGE]})
        result = await _run(client, _cfg, "status", property_value="done")
        assert "Task A" in result[0].text

    async def test_find_invalid_property_name_returns_error(self):
        client = FakeLogseqClient({"query_dsl": []})
        result = await _run(client, _cfg, "bad name!")
        assert "❌" in result[0].text
        assert not any(c[0] == "query_dsl" for c in client.calls)

    async def test_find_no_results(self):
        client = FakeLogseqClient({"query_dsl": []})
        result = await _run(client, _cfg, "missing-prop")
        assert "0" in result[0].text or "no" in result[0].text.lower()

    async def test_find_limit_respected(self):
        pages = [
            {
                "originalName": f"Page {i}",
                "name": f"page-{i}",
                "uuid": f"p{i}",
                "journal?": False,
            }
            for i in range(50)
        ]
        client = FakeLogseqClient({"query_dsl": pages})
        result = await _run(client, _cfg, "status", limit=5)
        assert "Page 0" in result[0].text
        assert "Page 49" not in result[0].text

    async def test_find_constructs_query_with_property(self):
        """The DSL query sent to the client should reference the property name."""
        captured = {}

        class CapturingClient(FakeLogseqClient):
            async def query_dsl(self, query):
                captured["query"] = query
                return []

        await _run(CapturingClient(), _cfg, "status")
        assert "status" in captured.get("query", "")

    async def test_find_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def query_dsl(self, query):
                raise RuntimeError("DB error")

        result = await _run(ErrorClient(), _cfg, "valid-prop")
        assert "❌ Error finding pages" in result[0].text
