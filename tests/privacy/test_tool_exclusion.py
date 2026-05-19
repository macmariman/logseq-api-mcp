"""Tests verifying that exclude_tags is enforced across all tools."""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient


def _page(name: str, tags: list | None = None) -> dict:
    return {
        "id": hash(name),
        "uuid": f"uuid-{name}",
        "originalName": name,
        "name": name.lower(),
        "journal?": False,
        "createdAt": 0,
        "updatedAt": 0,
        "properties": {"tags": tags} if tags else {},
    }


_SECRET = _page("Secret Page", tags=["private"])
_PUBLIC = _page("Public Page")
_cfg_excl = LogseqConfig("http://x", "t", exclude_tags=("private",))
_cfg_open = LogseqConfig("http://x", "t")


# ── get_all_pages ─────────────────────────────────────────────────────────────


class TestGetAllPagesExclusion:
    async def test_excluded_page_absent_from_listing(self):
        from src.tools.get_all_pages import get_all_pages as _run

        client = FakeLogseqClient({"get_all_pages": [_PUBLIC, _SECRET]})
        result = await _run(client, _cfg_excl)
        assert "Public Page" in result[0].text
        assert "Secret Page" not in result[0].text


# ── search ────────────────────────────────────────────────────────────────────


class TestSearchExclusion:
    async def test_excluded_page_absent_from_search_results(self):
        from src.tools.search import search as _run

        search_result = {
            "blocks": [],
            "pages": ["Secret Page", "Public Page"],
            "pages-content": [],
            "files": [],
        }
        pages = [_PUBLIC, _SECRET]
        client = FakeLogseqClient(
            {
                "search": search_result,
                "get_all_pages": pages,
                "excluded_page_names": frozenset({"secret page"}),
            }
        )
        result = await _run(client, _cfg_excl, "query")
        assert "Public Page" in result[0].text
        assert "Secret Page" not in result[0].text


# ── query ─────────────────────────────────────────────────────────────────────


class TestQueryExclusion:
    async def test_excluded_page_absent_from_query_results(self):
        from src.tools.query import query as _run

        items = [
            {
                "originalName": "Secret Page",
                "name": "secret page",
                "uuid": "p1",
                "journal?": False,
            },
            {
                "originalName": "Public Page",
                "name": "public page",
                "uuid": "p2",
                "journal?": False,
            },
        ]
        client = FakeLogseqClient(
            {
                "query_dsl": items,
                "get_all_pages": [_PUBLIC, _SECRET],
                "excluded_page_names": frozenset({"secret page"}),
            }
        )
        result = await _run(client, _cfg_excl, "[:find ?p]")
        assert "Public Page" in result[0].text
        assert "Secret Page" not in result[0].text


# ── find_pages_by_property ────────────────────────────────────────────────────


class TestFindPagesByPropertyExclusion:
    async def test_excluded_page_absent_from_property_results(self):
        from src.tools.find_pages_by_property import find_pages_by_property as _run

        items = [
            {"originalName": "Secret Page", "name": "secret page", "uuid": "p1"},
            {"originalName": "Public Page", "name": "public page", "uuid": "p2"},
        ]
        client = FakeLogseqClient(
            {
                "query_dsl": items,
                "get_all_pages": [_PUBLIC, _SECRET],
                "excluded_page_names": frozenset({"secret page"}),
            }
        )
        result = await _run(client, _cfg_excl, "status")
        assert "Public Page" in result[0].text
        assert "Secret Page" not in result[0].text


# ── get_all_page_content: access denied ───────────────────────────────────────


class TestGetAllPageContentExclusion:
    async def test_excluded_target_page_returns_access_denied(self):
        from src.tools.get_all_page_content import get_all_page_content as _run

        client = FakeLogseqClient(
            {
                "get_page": _SECRET,
                "get_page_blocks_tree": [],
                "get_all_pages": [_PUBLIC, _SECRET],
            }
        )
        result = await _run(client, _cfg_excl, "Secret Page")
        assert "❌" in result[0].text
        assert (
            "access" in result[0].text.lower()
            or "denied" in result[0].text.lower()
            or "excluded" in result[0].text.lower()
        )

    async def test_non_excluded_page_accessible(self):
        from src.tools.get_all_page_content import get_all_page_content as _run

        client = FakeLogseqClient(
            {
                "get_page": _PUBLIC,
                "get_page_blocks_tree": [],
                "get_all_pages": [_PUBLIC, _SECRET],
            }
        )
        result = await _run(client, _cfg_excl, "Public Page")
        assert "PAGE CONTENT" in result[0].text


# ── get_page_backlinks ────────────────────────────────────────────────────────


class TestGetPageBacklinksExclusion:
    async def test_excluded_source_page_absent_from_backlinks(self):
        from src.tools.get_page_backlinks import get_page_backlinks as _run

        linked_refs = [
            [
                {
                    "id": hash("Secret Page"),
                    "name": "secret page",
                    "originalName": "Secret Page",
                },
                {"uuid": "b1", "content": "ref"},
            ],
            [
                {
                    "id": hash("Public Page"),
                    "name": "public page",
                    "originalName": "Public Page",
                },
                {"uuid": "b2", "content": "ref"},
            ],
        ]
        client = FakeLogseqClient(
            {
                "get_page_linked_references": linked_refs,
                "get_all_pages": [_PUBLIC, _SECRET],
                "excluded_page_names": frozenset({"secret page"}),
            }
        )
        result = await _run(client, _cfg_excl, "Target Page")
        assert "Public Page" in result[0].text
        assert "Secret Page" not in result[0].text


# ── Cache-helper usage (E2) ───────────────────────────────────────────────────


class TestToolsUseExcludedPageNamesCache:
    """Tools must use cached `client.excluded_page_names()` instead of inline
    `get_all_pages()` for exclusion filtering."""

    async def test_search_uses_client_excluded_page_names_cache(
        self, fake_client, config
    ):
        fake_client.responses["excluded_page_names"] = frozenset({"secret"})
        fake_client.responses["search"] = {
            "blocks": [],
            "pages-content": [],
            "pages": ["Secret", "Public"],
            "files": [],
        }
        from src.tools.search import search

        result = await search(fake_client, config, query="anything")
        text = result[0].text
        assert "Secret" not in text
        assert "Public" in text
        assert any(c[0] == "excluded_page_names" for c in fake_client.calls)
        assert not any(c[0] == "get_all_pages" for c in fake_client.calls)

    async def test_query_uses_client_excluded_page_names_cache(
        self, fake_client, config
    ):
        fake_client.responses["excluded_page_names"] = frozenset({"secret"})
        fake_client.responses["query_dsl"] = [
            {"originalName": "Secret", "name": "secret", "uuid": "p1"},
            {"originalName": "Public", "name": "public", "uuid": "p2"},
        ]
        from src.tools.query import query

        result = await query(fake_client, config, query="[:find ?p]")
        text = result[0].text
        assert "Secret" not in text
        assert "Public" in text
        assert any(c[0] == "excluded_page_names" for c in fake_client.calls)
        assert not any(c[0] == "get_all_pages" for c in fake_client.calls)

    async def test_find_pages_by_property_uses_client_excluded_page_names_cache(
        self, fake_client, config
    ):
        fake_client.responses["excluded_page_names"] = frozenset({"secret"})
        fake_client.responses["query_dsl"] = [
            {"originalName": "Secret", "name": "secret", "uuid": "p1"},
            {"originalName": "Public", "name": "public", "uuid": "p2"},
        ]
        from src.tools.find_pages_by_property import find_pages_by_property

        result = await find_pages_by_property(fake_client, config, "status")
        text = result[0].text
        assert "Secret" not in text
        assert "Public" in text
        assert any(c[0] == "excluded_page_names" for c in fake_client.calls)
        assert not any(c[0] == "get_all_pages" for c in fake_client.calls)

    async def test_get_page_backlinks_uses_client_excluded_page_names_cache(
        self, fake_client, config
    ):
        fake_client.responses["excluded_page_names"] = frozenset({"secret"})
        fake_client.responses["get_page_linked_references"] = [
            [
                {"id": 1, "name": "secret", "originalName": "Secret"},
                {"uuid": "b1", "content": "ref"},
            ],
            [
                {"id": 2, "name": "public", "originalName": "Public"},
                {"uuid": "b2", "content": "ref"},
            ],
        ]
        from src.tools.get_page_backlinks import get_page_backlinks

        result = await get_page_backlinks(fake_client, config, "Target Page")
        text = result[0].text
        assert "Secret" not in text
        assert "Public" in text
        assert any(c[0] == "excluded_page_names" for c in fake_client.calls)
        assert not any(c[0] == "get_all_pages" for c in fake_client.calls)
