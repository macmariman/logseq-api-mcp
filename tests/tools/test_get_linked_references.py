"""Tests for the get_linked_references tool."""

import os
import time
from pathlib import Path

import pytest

from src.client.config import LogseqConfig
from src.tools.get_linked_references import (
    _journal_display_to_filename,
    get_linked_references,
)
from tests.conftest import FakeLogseqClient


class _TreeClient(FakeLogseqClient):
    """Fake client that returns a different page block tree per page name."""

    def __init__(
        self,
        trees_by_page: dict[str, list[dict]] | None = None,
        refs_by_tag: dict[str, list] | None = None,
        responses: dict | None = None,
    ):
        super().__init__(responses)
        self.trees_by_page = trees_by_page or {}
        self.refs_by_tag = refs_by_tag or {}

    async def get_page_blocks_tree(self, page_identifier: str) -> list[dict]:
        self.calls.append(("get_page_blocks_tree", (page_identifier,), {}))
        return self.trees_by_page.get(page_identifier, [])

    async def get_page_linked_references(self, page_name: str) -> list:
        self.calls.append(("get_page_linked_references", (page_name,), {}))
        # Fall back to FakeLogseqClient behavior if not configured per-tag.
        if page_name in self.refs_by_tag:
            return self.refs_by_tag[page_name]
        return self.responses.get("get_page_linked_references", [])


def _make_graph(tmp_path: Path) -> Path:
    (tmp_path / "pages").mkdir()
    (tmp_path / "journals").mkdir()
    return tmp_path


def _page(name: str, **extra) -> dict:
    return {"id": hash(name) & 0xFFFF, "name": name, "originalName": name, **extra}


def _block(uuid: str, content: str, children: list[dict] | None = None) -> dict:
    return {"uuid": uuid, "content": content, "children": children or []}


@pytest.mark.asyncio
async def test_returns_blocks_with_subtree():
    """A linking page whose tree contains [[tag]] yields the matching subtree."""
    tree = [
        _block(
            "u1",
            "- [[Kz/Inn Hub]]",
            children=[
                _block(
                    "u2",
                    "Puntos de dashes",
                    children=[_block("u3", "Re skilling up skilling")],
                )
            ],
        )
    ]
    client = _TreeClient(
        trees_by_page={"2026_05_26": tree},
        refs_by_tag={"Kz/Inn Hub": [[_page("2026_05_26")]]},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t")

    result = await get_linked_references(client, cfg, "Kz/Inn Hub")

    text = result[0].text
    assert "Found 1 reference to [[Kz/Inn Hub]]" in text
    assert "## 2026_05_26" in text
    assert "Puntos de dashes" in text
    assert "Re skilling up skilling" in text


@pytest.mark.asyncio
async def test_groups_by_source_page():
    client = _TreeClient(
        trees_by_page={
            "page-a": [_block("a", "- [[Tag]]", [_block("ac", "child of A")])],
            "page-b": [_block("b", "- [[Tag]]", [_block("bc", "child of B")])],
        },
        refs_by_tag={"Tag": [[_page("page-a")], [_page("page-b")]]},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t")

    text = (await get_linked_references(client, cfg, "Tag"))[0].text

    assert "## page-a" in text
    assert "## page-b" in text
    assert "child of A" in text
    assert "child of B" in text
    assert "Found 2 references to [[Tag]]" in text


@pytest.mark.asyncio
async def test_since_days_filters_by_mtime(tmp_path: Path):
    graph = _make_graph(tmp_path)
    recent = graph / "journals" / "2026_05_26.md"
    old = graph / "journals" / "2022_01_01.md"
    recent.write_text("- [[Tag]]\n")
    old.write_text("- [[Tag]]\n")
    two_years_ago = time.time() - (730 * 86400)
    os.utime(old, (two_years_ago, two_years_ago))

    client = _TreeClient(
        trees_by_page={
            "2026_05_26": [_block("r", "- [[Tag]]", [_block("rc", "recent child")])],
            "2022_01_01": [_block("o", "- [[Tag]]", [_block("oc", "old child")])],
        },
        refs_by_tag={"Tag": [[_page("2026_05_26")], [_page("2022_01_01")]]},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    text = (await get_linked_references(client, cfg, "Tag", since_days=30))[0].text

    assert "## 2026_05_26" in text
    assert "## 2022_01_01" not in text
    assert "recent child" in text
    assert "old child" not in text
    assert "last 30 days" in text


@pytest.mark.asyncio
async def test_since_days_without_graph_path_errors():
    cfg = LogseqConfig(endpoint="http://x", token="t")

    result = await get_linked_references(FakeLogseqClient(), cfg, "Tag", since_days=7)

    assert "❌" in result[0].text
    assert "LOGSEQ_GRAPH_PATH" in result[0].text


@pytest.mark.asyncio
async def test_limit_caps_total_matches(tmp_path: Path):
    graph = _make_graph(tmp_path)
    now = time.time()
    for i, name in enumerate(["p1.md", "p2.md", "p3.md"]):
        p = graph / "pages" / name
        p.write_text("- [[Tag]]\n")
        os.utime(p, (now - i, now - i))  # p1 newest, p3 oldest

    client = _TreeClient(
        trees_by_page={
            "p1": [_block("u1", "- [[Tag]]", [_block("u1c", "from p1")])],
            "p2": [_block("u2", "- [[Tag]]", [_block("u2c", "from p2")])],
            "p3": [_block("u3", "- [[Tag]]", [_block("u3c", "from p3")])],
        },
        refs_by_tag={"Tag": [[_page("p1")], [_page("p2")], [_page("p3")]]},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    text = (await get_linked_references(client, cfg, "Tag", limit=2))[0].text

    assert "## p1" in text
    assert "## p2" in text
    assert "## p3" not in text
    assert "from p3" not in text
    # New limit semantics: early-break + "limit reached" wording (no total).
    assert "Showing 2 references to [[Tag]]" in text
    assert "limit reached" in text
    # The early-break optimization must skip the fetch for p3 entirely.
    fetched = [c[1][0] for c in client.calls if c[0] == "get_page_blocks_tree"]
    assert "p3" not in fetched, f"p3 should not have been fetched, got {fetched}"


@pytest.mark.asyncio
async def test_include_namespace_children_unions_descendants():
    client = _TreeClient(
        trees_by_page={
            "parent-page": [_block("p1", "- [[Tag]]", [_block("p1c", "parent child")])],
            "child-page": [_block("c1", "- [[Tag/Sub]]", [_block("c1c", "ns child")])],
        },
        refs_by_tag={
            "Tag": [[_page("parent-page")]],
            "Tag/Sub": [[_page("child-page")]],
        },
        responses={"get_pages_from_namespace": [_page("Tag/Sub")]},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t")

    text = (
        await get_linked_references(client, cfg, "Tag", include_namespace_children=True)
    )[0].text

    assert "parent child" in text
    assert "ns child" in text
    assert "including namespace children" in text
    assert "Found 2 references to [[Tag]]" in text


@pytest.mark.asyncio
async def test_dedup_nested_match_keeps_highest_ancestor():
    """Parent block has [[Tag]] and a nested descendant also has [[Tag]]:
    only the parent (with its full subtree) should be rendered."""
    tree = [
        _block(
            "parent",
            "- [[Tag]] heading",
            children=[_block("nested", "- nested [[Tag]] mention")],
        )
    ]
    client = _TreeClient(
        trees_by_page={"page-x": tree},
        refs_by_tag={"Tag": [[_page("page-x")]]},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t")

    text = (await get_linked_references(client, cfg, "Tag"))[0].text

    # The substring "nested [[Tag]] mention" appears exactly once — inside the
    # parent's rendered subtree, not duplicated as its own top-level entry.
    assert text.count("nested [[Tag]] mention") == 1
    # Total count reflects post-dedup matches (just the parent).
    assert "Found 1 reference to [[Tag]]" in text


@pytest.mark.asyncio
async def test_excluded_tags_drops_source_page():
    client = _TreeClient(
        trees_by_page={
            "kept-page": [_block("k", "- [[Tag]]", [_block("kc", "kept content")])],
            "excluded-page": [
                _block("e", "- [[Tag]]", [_block("ec", "excluded content")])
            ],
        },
        refs_by_tag={"Tag": [[_page("kept-page")], [_page("excluded-page")]]},
        responses={"excluded_page_names": frozenset({"excluded-page"})},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t")

    text = (await get_linked_references(client, cfg, "Tag"))[0].text

    assert "kept content" in text
    assert "excluded content" not in text
    assert "## excluded-page" not in text


@pytest.mark.asyncio
async def test_no_matches_returns_friendly_message():
    """API returns linking pages but none of their trees contain [[tag]]."""
    client = _TreeClient(
        trees_by_page={"some-page": [_block("x", "- unrelated content")]},
        refs_by_tag={"DoesNotExist": [[_page("some-page")]]},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t")

    text = (await get_linked_references(client, cfg, "DoesNotExist"))[0].text

    assert "Found 0 references to [[DoesNotExist]]" in text


@pytest.mark.asyncio
async def test_api_returns_no_linking_pages():
    """API returns an empty list of linking pages entirely."""
    client = FakeLogseqClient(responses={"get_page_linked_references": []})
    cfg = LogseqConfig(endpoint="http://x", token="t")

    text = (await get_linked_references(client, cfg, "Nope"))[0].text

    assert "Found 0 references to [[Nope]]" in text


@pytest.mark.asyncio
async def test_empty_tag_returns_error():
    cfg = LogseqConfig(endpoint="http://x", token="t")

    result = await get_linked_references(FakeLogseqClient(), cfg, "   ")

    assert "❌" in result[0].text
    assert "non-empty" in result[0].text


@pytest.mark.asyncio
async def test_negative_since_days_returns_error():
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path="/tmp")

    result = await get_linked_references(FakeLogseqClient(), cfg, "Tag", since_days=-1)

    assert "❌" in result[0].text
    assert "non-negative" in result[0].text


@pytest.mark.asyncio
async def test_namespace_substring_does_not_match_parent():
    """``[[Kz/Inn Hub/CCAF]]`` must NOT match a search for ``Kz/Inn Hub``.

    The exact-string check ``[[Kz/Inn Hub]]`` doesn't appear inside
    ``[[Kz/Inn Hub/CCAF]]`` so a parent-namespace search stays precise.
    """
    client = _TreeClient(
        trees_by_page={
            "page-with-child-ref": [_block("x", "- [[Kz/Inn Hub/CCAF]] only the child")]
        },
        refs_by_tag={"Kz/Inn Hub": [[_page("page-with-child-ref")]]},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t")

    text = (await get_linked_references(client, cfg, "Kz/Inn Hub"))[0].text

    assert "Found 0 references to [[Kz/Inn Hub]]" in text


def test_journal_display_to_filename_parses_default_format():
    assert _journal_display_to_filename("Jan 22nd, 2026") == "2026_01_22"
    assert _journal_display_to_filename("May 6th, 2026") == "2026_05_06"
    assert _journal_display_to_filename("Dec 1st, 2025") == "2025_12_01"
    assert _journal_display_to_filename("Aug 3rd, 2024") == "2024_08_03"
    assert _journal_display_to_filename("Feb 11th, 2025") == "2025_02_11"
    # Non-matches return None.
    assert _journal_display_to_filename("Current Projects") is None
    assert _journal_display_to_filename("2026_01_22") is None
    assert _journal_display_to_filename("") is None


@pytest.mark.asyncio
async def test_since_days_resolves_journal_display_names(tmp_path: Path):
    """Linking pages with journal display names should still be timestamped."""
    graph = _make_graph(tmp_path)
    # Recent journal: file lives at journals/2026_05_26.md but API returns
    # the display name "May 26th, 2026".
    recent = graph / "journals" / "2026_05_26.md"
    recent.write_text("- [[Tag]]\n")

    client = _TreeClient(
        trees_by_page={
            "May 26th, 2026": [
                _block("r", "- [[Tag]]", [_block("rc", "recent journal child")])
            ],
        },
        refs_by_tag={"Tag": [[_page("May 26th, 2026")]]},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    text = (await get_linked_references(client, cfg, "Tag", since_days=30))[0].text

    assert "## May 26th, 2026" in text
    assert "recent journal child" in text


@pytest.mark.asyncio
async def test_found_zero_includes_active_filter_notes(tmp_path: Path):
    """When a filter (since_days) excludes everything, the empty-result
    message must surface the filter so the user doesn't think the tag itself
    has no references."""
    graph = _make_graph(tmp_path)
    # File exists but is way older than the 7-day window.
    old = graph / "pages" / "old-page.md"
    old.write_text("- [[Tag]]\n")
    one_year_ago = time.time() - (365 * 86400)
    os.utime(old, (one_year_ago, one_year_ago))

    client = _TreeClient(
        trees_by_page={"old-page": [_block("o", "- [[Tag]]", [_block("oc", "old")])]},
        refs_by_tag={"Tag": [[_page("old-page")]]},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    text = (await get_linked_references(client, cfg, "Tag", since_days=7))[0].text

    assert "Found 0 references to [[Tag]]" in text
    assert "last 7 days" in text  # filter must appear in the empty message


@pytest.mark.asyncio
async def test_limit_zero_short_circuits():
    """limit=0 returns immediately with a clear message — no work done."""
    client = _TreeClient(
        trees_by_page={"page-a": [_block("a", "- [[Tag]]")]},
        refs_by_tag={"Tag": [[_page("page-a")]]},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t")

    text = (await get_linked_references(client, cfg, "Tag", limit=0))[0].text

    assert "Found 0 references to [[Tag]]" in text
    assert "limit=0" in text
    # No tree fetches at all — the short-circuit precedes the API loop.
    fetched = [c for c in client.calls if c[0] == "get_page_blocks_tree"]
    assert fetched == []


@pytest.mark.asyncio
async def test_negative_limit_returns_error():
    cfg = LogseqConfig(endpoint="http://x", token="t")

    result = await get_linked_references(FakeLogseqClient(), cfg, "Tag", limit=-3)

    assert "❌" in result[0].text
    assert "limit" in result[0].text.lower()
    assert "non-negative" in result[0].text


@pytest.mark.asyncio
async def test_since_days_zero_means_today(tmp_path: Path):
    """since_days=0 must mean 'modified today' (since local midnight), not
    'modified at this exact second'."""
    graph = _make_graph(tmp_path)
    # Two files: one modified earlier today, one modified yesterday.
    today_path = graph / "pages" / "today.md"
    today_path.write_text("- [[Tag]]\n")
    # Modify earlier today by setting mtime to (now - 3 hours). Still after
    # local midnight on most days; the test asserts it survives the filter.
    earlier_today = time.time() - (3 * 3600)
    os.utime(today_path, (earlier_today, earlier_today))

    yesterday_path = graph / "pages" / "yesterday.md"
    yesterday_path.write_text("- [[Tag]]\n")
    # Two days ago to safely land before any "today" anchor across DST/tz.
    two_days_ago = time.time() - (2 * 86400)
    os.utime(yesterday_path, (two_days_ago, two_days_ago))

    client = _TreeClient(
        trees_by_page={
            "today": [_block("t", "- [[Tag]]", [_block("tc", "today content")])],
            "yesterday": [_block("y", "- [[Tag]]", [_block("yc", "old content")])],
        },
        refs_by_tag={"Tag": [[_page("today")], [_page("yesterday")]]},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    text = (await get_linked_references(client, cfg, "Tag", since_days=0))[0].text

    assert "today content" in text
    assert "old content" not in text
    assert "today only" in text


@pytest.mark.asyncio
async def test_handles_client_exception():
    class Broken(FakeLogseqClient):
        async def get_page_linked_references(self, page_name: str) -> list:
            raise RuntimeError("api down")

    cfg = LogseqConfig(endpoint="http://x", token="t")

    result = await get_linked_references(Broken(), cfg, "Tag")

    assert "❌" in result[0].text
    assert "api down" in result[0].text


# ── Hashtag syntax tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bare_hashtag_matches():
    """``#meeting`` in block content matches a search for ``meeting``."""
    client = _TreeClient(
        trees_by_page={"p": [_block("u1", "#meeting great session")]},
        refs_by_tag={"meeting": [[_page("p")]]},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t")

    text = (await get_linked_references(client, cfg, "meeting"))[0].text

    assert "Found 1 reference to [[meeting]]" in text
    assert "great session" in text


@pytest.mark.asyncio
async def test_bare_hashtag_at_end_of_content_matches():
    """``#meeting`` at the very end of a block (no trailing space) still matches."""
    client = _TreeClient(
        trees_by_page={"p": [_block("u1", "notes from #meeting")]},
        refs_by_tag={"meeting": [[_page("p")]]},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t")

    text = (await get_linked_references(client, cfg, "meeting"))[0].text

    assert "Found 1 reference to [[meeting]]" in text


@pytest.mark.asyncio
async def test_bare_hashtag_no_prefix_false_positive():
    """``#meeting`` must NOT match a block that only contains ``#meetings``."""
    client = _TreeClient(
        trees_by_page={"p": [_block("u1", "attending #meetings today")]},
        refs_by_tag={"meeting": [[_page("p")]]},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t")

    text = (await get_linked_references(client, cfg, "meeting"))[0].text

    assert "Found 0 references to [[meeting]]" in text


@pytest.mark.asyncio
async def test_bracket_hashtag_matches_multiword_tag():
    """``#[[Kz/Inn Hub]]`` in block content matches a search for ``Kz/Inn Hub``."""
    client = _TreeClient(
        trees_by_page={"p": [_block("u1", "#[[Kz/Inn Hub]] standup notes")]},
        refs_by_tag={"Kz/Inn Hub": [[_page("p")]]},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t")

    text = (await get_linked_references(client, cfg, "Kz/Inn Hub"))[0].text

    assert "Found 1 reference to [[Kz/Inn Hub]]" in text
    assert "standup notes" in text


@pytest.mark.asyncio
async def test_tag_with_spaces_does_not_generate_bare_hashtag():
    """Tags with spaces must not generate a bare ``#Tag`` ref string
    (it would never appear in Logseq content without brackets)."""
    client = _TreeClient(
        # Only bare #Kz/Inn Hub (invalid in Logseq) — should NOT match.
        trees_by_page={"p": [_block("u1", "#Kz/Inn Hub notes")]},
        refs_by_tag={"Kz/Inn Hub": [[_page("p")]]},
    )
    cfg = LogseqConfig(endpoint="http://x", token="t")

    text = (await get_linked_references(client, cfg, "Kz/Inn Hub"))[0].text

    # Neither [[Kz/Inn Hub]] nor #[[Kz/Inn Hub]] appears in content.
    assert "Found 0 references to [[Kz/Inn Hub]]" in text
