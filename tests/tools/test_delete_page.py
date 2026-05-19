"""Tests for delete_page tool."""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.delete_page import _run

_cfg = LogseqConfig("http://x", "t")
_page = {"id": 1, "uuid": "page-uuid", "originalName": "Old Page"}


class TestDeletePage:
    async def test_delete_page_success(self):
        client = FakeLogseqClient({"get_page": _page})
        result = await _run(client, _cfg, "Old Page")
        assert any(c[0] == "delete_page" for c in client.calls)
        assert "deleted" in result[0].text.lower()

    async def test_delete_page_returns_confirmation_message(self):
        client = FakeLogseqClient({"get_page": _page})
        result = await _run(client, _cfg, "Old Page")
        assert "Old Page" in result[0].text
        assert "✅" in result[0].text

    async def test_delete_page_not_found_returns_error(self):
        client = FakeLogseqClient({"get_page": None})
        result = await _run(client, _cfg, "Ghost Page")
        assert "❌" in result[0].text
        assert not any(c[0] == "delete_page" for c in client.calls)

    async def test_delete_page_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_page(self, name):
                raise RuntimeError("API down")

        result = await _run(ErrorClient(), _cfg, "Some Page")
        assert "❌ Error deleting page" in result[0].text

    async def test_delete_page_calls_client_delete(self):
        client = FakeLogseqClient({"get_page": _page})
        await _run(client, _cfg, "Old Page")
        delete_calls = [c for c in client.calls if c[0] == "delete_page"]
        assert len(delete_calls) == 1
        assert delete_calls[0][1][0] == "Old Page"
