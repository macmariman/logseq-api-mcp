"""Tests for append_block_in_page tool."""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.append_block_in_page import append_block_in_page as _run

_cfg = LogseqConfig("http://x", "t")


class TestAppendBlockInPage:
    async def test_success_message(self):
        client = FakeLogseqClient({"append_block_in_page": {"uuid": "new-uuid"}})
        result = await _run(client, _cfg, "My Page", "new content")
        assert "BLOCK APPENDED SUCCESSFULLY" in result[0].text
        assert "My Page" in result[0].text
        assert "new content" in result[0].text

    async def test_shows_before_positioning(self):
        client = FakeLogseqClient({"append_block_in_page": {"uuid": "x"}})
        result = await _run(client, _cfg, "My Page", "content", before="block-uuid")
        assert "before block: block-uuid" in result[0].text

    async def test_shows_sibling_positioning(self):
        client = FakeLogseqClient({"append_block_in_page": {"uuid": "x"}})
        result = await _run(client, _cfg, "My Page", "content", sibling="sibling-uuid")
        assert "sibling of: sibling-uuid" in result[0].text

    async def test_default_end_of_page_message(self):
        client = FakeLogseqClient({"append_block_in_page": {"uuid": "x"}})
        result = await _run(client, _cfg, "My Page", "content")
        assert "At the end of the page" in result[0].text

    async def test_no_response_returns_error(self):
        client = FakeLogseqClient({"append_block_in_page": None})
        result = await _run(client, _cfg, "My Page", "content")
        assert "No response from Logseq API" in result[0].text

    async def test_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def append_block_in_page(self, page, content, options=None):
                raise RuntimeError("refused")

        result = await _run(ErrorClient(), _cfg, "My Page", "content")
        assert "❌ Error appending block: refused" in result[0].text
