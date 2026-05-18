"""Tests for rename_page tool."""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.rename_page import _run

_cfg = LogseqConfig("http://x", "t")
_page = {"id": 1, "uuid": "page-uuid", "originalName": "Old Name"}


class TestRenamePage:
    async def test_rename_page_success(self):
        client = FakeLogseqClient({"get_page": _page})
        result = await _run(client, _cfg, "Old Name", "New Name")
        assert any(c[0] == "rename_page" for c in client.calls)
        assert "✅" in result[0].text

    async def test_rename_page_shows_old_and_new_name(self):
        client = FakeLogseqClient({"get_page": _page})
        result = await _run(client, _cfg, "Old Name", "New Name")
        assert "Old Name" in result[0].text
        assert "New Name" in result[0].text

    async def test_rename_page_same_name_is_error(self):
        client = FakeLogseqClient({"get_page": _page})
        result = await _run(client, _cfg, "Old Name", "Old Name")
        assert "❌" in result[0].text
        assert not any(c[0] == "rename_page" for c in client.calls)

    async def test_rename_page_empty_new_name_is_error(self):
        client = FakeLogseqClient({"get_page": _page})
        result = await _run(client, _cfg, "Old Name", "")
        assert "❌" in result[0].text
        assert not any(c[0] == "rename_page" for c in client.calls)

    async def test_rename_page_not_found_is_error(self):
        client = FakeLogseqClient({"get_page": None})
        result = await _run(client, _cfg, "Ghost", "New Name")
        assert "❌" in result[0].text
        assert not any(c[0] == "rename_page" for c in client.calls)

    async def test_rename_page_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_page(self, name):
                raise RuntimeError("timeout")

        result = await _run(ErrorClient(), _cfg, "Old", "New")
        assert "❌ Error renaming page" in result[0].text
