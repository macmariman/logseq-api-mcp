"""Tests for get_pages_from_namespace tool."""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.get_pages_from_namespace import get_pages_from_namespace as _run

_cfg = LogseqConfig("http://x", "t")

_NS_PAGES = [
    {
        "id": 1,
        "uuid": "p1",
        "originalName": "Project/Alpha",
        "name": "project/alpha",
        "journal?": False,
        "createdAt": 0,
        "updatedAt": 0,
    },
    {
        "id": 2,
        "uuid": "p2",
        "originalName": "Project/Beta",
        "name": "project/beta",
        "journal?": False,
        "createdAt": 0,
        "updatedAt": 0,
    },
]


class TestGetPagesFromNamespace:
    async def test_returns_namespace_pages(self):
        client = FakeLogseqClient({"get_pages_from_namespace": _NS_PAGES})
        result = await _run(client, _cfg, "Project")
        assert "Project/Alpha" in result[0].text
        assert "Project/Beta" in result[0].text

    async def test_empty_namespace_shows_message(self):
        client = FakeLogseqClient({"get_pages_from_namespace": []})
        result = await _run(client, _cfg, "Empty")
        assert "Empty" in result[0].text
        assert "no pages" in result[0].text.lower() or "0" in result[0].text

    async def test_shows_page_count(self):
        client = FakeLogseqClient({"get_pages_from_namespace": _NS_PAGES})
        result = await _run(client, _cfg, "Project")
        assert "2" in result[0].text

    async def test_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_pages_from_namespace(self, namespace):
                raise RuntimeError("namespace error")

        result = await _run(ErrorClient(), _cfg, "Broken")
        assert "❌ Error fetching namespace pages" in result[0].text

    async def test_calls_client_with_correct_namespace(self):
        client = FakeLogseqClient({"get_pages_from_namespace": _NS_PAGES})
        await _run(client, _cfg, "Project")
        ns_calls = [c for c in client.calls if c[0] == "get_pages_from_namespace"]
        assert ns_calls[0][1][0] == "Project"
