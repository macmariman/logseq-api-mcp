"""Tests for create_page tool."""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.create_page import _run

_cfg = LogseqConfig("http://x", "t")
_page_result = {
    "id": 1,
    "uuid": "new-uuid",
    "originalName": "New Page",
    "format": "markdown",
    "journal?": False,
}


class TestCreatePage:
    # ── basic behaviour ───────────────────────────────────────────────────────

    async def test_success_message(self):
        client = FakeLogseqClient({"create_page": _page_result})
        result = await _run(client, _cfg, "New Page")
        assert "PAGE CREATED SUCCESSFULLY" in result[0].text
        assert "New Page" in result[0].text

    async def test_shows_page_uuid(self):
        page_result = {
            "id": 1,
            "uuid": "abc-123",
            "originalName": "My Page",
            "format": "markdown",
            "journal?": False,
        }
        client = FakeLogseqClient({"create_page": page_result})
        result = await _run(client, _cfg, "My Page")
        assert "abc-123" in result[0].text

    async def test_no_response_returns_error(self):
        client = FakeLogseqClient({"create_page": None})
        result = await _run(client, _cfg, "My Page")
        assert "No response from Logseq API" in result[0].text

    async def test_properties_count_shown(self):
        client = FakeLogseqClient({"create_page": _page_result})
        result = await _run(
            client, _cfg, "P", properties={"status": "active", "priority": "high"}
        )
        assert "Properties set: 2 items" in result[0].text

    async def test_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def create_page(self, title, properties=None, fmt=None):
                raise RuntimeError("API unavailable")

        result = await _run(ErrorClient(), _cfg, "My Page")
        assert "❌ Error creating page: API unavailable" in result[0].text

    # ── content parameter ─────────────────────────────────────────────────────

    async def test_content_triggers_insert_batch_block(self):
        """When content is provided, blocks are inserted via insert_batch_block."""
        client = FakeLogseqClient(
            {
                "create_page": _page_result,
                "insert_batch_block": [],
            }
        )
        await _run(client, _cfg, "New Page", content="- Item one\n- Item two")
        assert any(c[0] == "insert_batch_block" for c in client.calls)

    async def test_content_none_skips_insert_batch_block(self):
        """No content → no insert_batch_block call."""
        client = FakeLogseqClient({"create_page": _page_result})
        await _run(client, _cfg, "New Page", content=None)
        assert not any(c[0] == "insert_batch_block" for c in client.calls)

    async def test_content_blocks_counted_in_output(self):
        """Result text mentions blocks inserted."""
        client = FakeLogseqClient(
            {
                "create_page": _page_result,
                "insert_batch_block": [],
            }
        )
        result = await _run(client, _cfg, "New Page", content="- Item one\n- Item two")
        assert "block" in result[0].text.lower()

    async def test_frontmatter_merged_with_properties(self):
        """Frontmatter props from content are merged with explicit properties."""
        md = "---\nstatus: active\n---\n- block content"
        create_call_args = {}

        class CapturingClient(FakeLogseqClient):
            async def create_page(self, title, properties=None, fmt=None):
                create_call_args["properties"] = properties
                return _page_result

        capturing = CapturingClient({"insert_batch_block": []})
        await _run(
            capturing, _cfg, "New Page", content=md, properties={"priority": "high"}
        )
        props = create_call_args.get("properties", {})
        assert props.get("status") == "active"
        assert props.get("priority") == "high"

    async def test_empty_content_skips_insert_batch_block(self):
        """Empty/whitespace content → no insert_batch_block call."""
        client = FakeLogseqClient({"create_page": _page_result})
        await _run(client, _cfg, "New Page", content="   \n  ")
        assert not any(c[0] == "insert_batch_block" for c in client.calls)
