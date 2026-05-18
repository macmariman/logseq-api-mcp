"""Tests for create_page tool."""

from tests.conftest import FakeLogseqClient
from src.tools.create_page import _run


class TestCreatePage:
    async def test_success_message(self):
        page_result = {"id": 1, "uuid": "new-uuid", "originalName": "New Page", "format": "markdown", "journal?": False}
        client = FakeLogseqClient({"create_page": page_result})
        result = await _run(client, "New Page")
        assert "PAGE CREATED SUCCESSFULLY" in result[0].text
        assert "New Page" in result[0].text

    async def test_shows_page_uuid(self):
        page_result = {"id": 1, "uuid": "abc-123", "originalName": "My Page", "format": "markdown", "journal?": False}
        client = FakeLogseqClient({"create_page": page_result})
        result = await _run(client, "My Page")
        assert "abc-123" in result[0].text

    async def test_no_response_returns_error(self):
        client = FakeLogseqClient({"create_page": None})
        result = await _run(client, "My Page")
        assert "No response from Logseq API" in result[0].text

    async def test_properties_count_shown(self):
        page_result = {"id": 1, "uuid": "x", "originalName": "P", "format": "markdown", "journal?": False}
        client = FakeLogseqClient({"create_page": page_result})
        result = await _run(client, "P", properties={"status": "active", "priority": "high"})
        assert "Properties set: 2 items" in result[0].text

    async def test_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def create_page(self, title, properties=None, fmt=None):
                raise RuntimeError("API unavailable")

        result = await _run(ErrorClient(), "My Page")
        assert "❌ Error creating page: API unavailable" in result[0].text
