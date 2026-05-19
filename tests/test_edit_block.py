"""Tests for edit_block tool."""

from tests.conftest import FakeLogseqClient
from src.tools.edit_block import _run


class TestEditBlock:
    async def test_success_message(self):
        client = FakeLogseqClient({"edit_block": {"uuid": "block-123"}})
        result = await _run(client, "block-123", content="updated content")
        assert "BLOCK EDITED SUCCESSFULLY" in result[0].text
        assert "block-123" in result[0].text

    async def test_content_update_shown(self):
        client = FakeLogseqClient({"edit_block": {"uuid": "b"}})
        result = await _run(client, "b", content="new content")
        assert "Content updated" in result[0].text
        assert "new content" in result[0].text

    async def test_properties_update_shown(self):
        client = FakeLogseqClient({"edit_block": {"uuid": "b"}})
        result = await _run(client, "b", properties={"status": "done"})
        assert "Properties updated" in result[0].text

    async def test_cursor_position_shown(self):
        client = FakeLogseqClient({"edit_block": {"uuid": "b"}})
        result = await _run(client, "b", content="text", cursor_position=5)
        assert "Cursor positioned at index 5" in result[0].text

    async def test_focus_enabled_shown(self):
        client = FakeLogseqClient({"edit_block": {"uuid": "b"}})
        result = await _run(client, "b", focus=True)
        assert "Focus: Enabled" in result[0].text

    async def test_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def edit_block(self, block_uuid, **kwargs):
                raise RuntimeError("lost connection")

        result = await _run(ErrorClient(), "b", content="text")
        assert "❌ Error editing block: lost connection" in result[0].text
