"""Tests for get_all_pages tool."""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.get_all_pages import get_all_pages as _run


def _page(name: str, journal: bool = False, tags: list | None = None) -> dict:
    props = {"tags": tags} if tags else {}
    return {
        "id": hash(name),
        "uuid": f"uuid-{name}",
        "originalName": name,
        "name": name,
        "journal?": journal,
        "createdAt": 0,
        "updatedAt": 0,
        "properties": props,
    }


class TestGetAllPages:
    """Test cases for get_all_pages()."""

    async def test_success_shows_listing_header(self):
        client = FakeLogseqClient({"get_all_pages": [_page("Test Page")]})
        result = await _run(client, LogseqConfig("http://x", "t"))
        assert "📊 **LOGSEQ PAGES LISTING**" in result[0].text
        assert "Test Page" in result[0].text

    async def test_with_start_end_limits(self):
        pages = [_page(f"Page {i}") for i in range(10)]
        client = FakeLogseqClient({"get_all_pages": pages})
        result = await _run(client, LogseqConfig("http://x", "t"), start=0, end=3)
        assert "showing indices 0-3" in result[0].text

    async def test_empty_returns_no_pages_message(self):
        client = FakeLogseqClient({"get_all_pages": []})
        result = await _run(client, LogseqConfig("http://x", "t"))
        assert "No pages found in Logseq graph" in result[0].text

    async def test_separates_journals_from_regular(self):
        pages = [_page("Regular"), _page("2024-01-01", journal=True)]
        client = FakeLogseqClient({"get_all_pages": pages})
        result = await _run(client, LogseqConfig("http://x", "t"))
        assert "REGULAR PAGES" in result[0].text
        assert "JOURNAL PAGES" in result[0].text

    # ── include_journals ──────────────────────────────────────────────────────

    async def test_include_journals_false_hides_journals(self):
        pages = [_page("Regular"), _page("2024-01-01", journal=True)]
        client = FakeLogseqClient({"get_all_pages": pages})
        result = await _run(
            client, LogseqConfig("http://x", "t"), include_journals=False
        )
        assert "JOURNAL PAGES" not in result[0].text
        assert "2024-01-01" not in result[0].text

    async def test_include_journals_true_shows_journals(self):
        pages = [_page("Regular"), _page("2024-01-01", journal=True)]
        client = FakeLogseqClient({"get_all_pages": pages})
        result = await _run(
            client, LogseqConfig("http://x", "t"), include_journals=True
        )
        assert "2024-01-01" in result[0].text

    async def test_include_journals_default_shows_journals(self):
        """Default is True — journals shown by default."""
        pages = [_page("Regular"), _page("2024-01-01", journal=True)]
        client = FakeLogseqClient({"get_all_pages": pages})
        result = await _run(client, LogseqConfig("http://x", "t"))
        assert "JOURNAL PAGES" in result[0].text

    # ── exclude_tags ──────────────────────────────────────────────────────────

    async def test_exclude_tags_hides_tagged_pages(self):
        pages = [_page("Public"), _page("Secret", tags=["private"])]
        cfg = LogseqConfig("http://x", "t", exclude_tags=("private",))
        client = FakeLogseqClient({"get_all_pages": pages})
        result = await _run(client, cfg)
        assert "Public" in result[0].text
        assert "Secret" not in result[0].text

    async def test_exclude_tags_empty_shows_all(self):
        pages = [_page("Public"), _page("Secret", tags=["private"])]
        cfg = LogseqConfig("http://x", "t", exclude_tags=())
        client = FakeLogseqClient({"get_all_pages": pages})
        result = await _run(client, cfg)
        assert "Secret" in result[0].text

    async def test_exclude_tags_multiple_tags(self):
        pages = [
            _page("PageAlpha"),
            _page("PageBeta", tags=["private"]),
            _page("PageGamma", tags=["secret"]),
        ]
        cfg = LogseqConfig("http://x", "t", exclude_tags=("private", "secret"))
        client = FakeLogseqClient({"get_all_pages": pages})
        result = await _run(client, cfg)
        assert "PageAlpha" in result[0].text
        assert "PageBeta" not in result[0].text
        assert "PageGamma" not in result[0].text

    # ── error handling ────────────────────────────────────────────────────────

    async def test_exception_returns_error_message(self):
        class ErrorClient(FakeLogseqClient):
            async def get_all_pages(self):
                raise RuntimeError("Network error")

        result = await _run(ErrorClient(), LogseqConfig("http://x", "t"))
        assert "❌ Error fetching pages: Network error" in result[0].text
