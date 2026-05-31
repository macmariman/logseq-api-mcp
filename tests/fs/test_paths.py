"""Tests for src/fs/paths.py — pure, no mocks."""

from pathlib import Path

from src.fs.paths import (
    draw_name_to_filename,
    page_name_to_filename,
    resolve_draw_path,
    resolve_page_path,
    target_path_for_draw,
)


# ── page_name_to_filename ────────────────────────────────────────────────────


def test_plain_name_just_appends_md():
    assert page_name_to_filename("Hello World") == "Hello World.md"


def test_slash_is_url_encoded():
    assert page_name_to_filename("Foo/Bar") == "Foo%2FBar.md"


def test_hash_is_url_encoded():
    assert page_name_to_filename("#Workout") == "%23Workout.md"


def test_colon_is_url_encoded():
    assert page_name_to_filename("440 – Levels: Programming") == (
        "440 – Levels%3A Programming.md"
    )


def test_percent_encoded_before_others_to_avoid_double_encoding():
    # A literal '%' in the page name becomes %25, never %2525.
    assert page_name_to_filename("50% off") == "50%25 off.md"


def test_multiple_specials_each_encoded():
    assert page_name_to_filename("a/b#c:d") == "a%2Fb%23c%3Ad.md"


def test_parens_and_quotes_kept_literal():
    # Logseq leaves filesystem-safe chars alone — observed in real graph files.
    assert page_name_to_filename("(draft) it's fine") == "(draft) it's fine.md"


# ── resolve_page_path ────────────────────────────────────────────────────────


def test_resolve_returns_none_when_graph_path_empty():
    assert resolve_page_path("", "Foo") is None


def test_resolve_returns_none_when_file_missing(tmp_path: Path):
    (tmp_path / "pages").mkdir()
    assert resolve_page_path(str(tmp_path), "Missing") is None


def test_resolve_finds_in_pages(tmp_path: Path):
    pages = tmp_path / "pages"
    pages.mkdir()
    target = pages / "Hello.md"
    target.write_text("hi")
    assert resolve_page_path(str(tmp_path), "Hello") == target.resolve()


def test_resolve_finds_encoded_name(tmp_path: Path):
    pages = tmp_path / "pages"
    pages.mkdir()
    target = pages / "Foo%2FBar.md"
    target.write_text("hi")
    assert resolve_page_path(str(tmp_path), "Foo/Bar") == target.resolve()


def test_resolve_falls_back_to_journals(tmp_path: Path):
    (tmp_path / "pages").mkdir()
    journals = tmp_path / "journals"
    journals.mkdir()
    target = journals / "2026_05_26.md"
    target.write_text("today")
    assert resolve_page_path(str(tmp_path), "2026_05_26") == target.resolve()


def test_resolve_rejects_path_traversal(tmp_path: Path):
    # Build a file OUTSIDE the graph that a malicious page name could target.
    outside = tmp_path.parent / "outside.md"
    outside.write_text("secret")
    graph = tmp_path / "graph"
    (graph / "pages").mkdir(parents=True)
    # "../outside" should not be resolvable through the pages dir.
    assert resolve_page_path(str(graph), "../outside") is None


# ── draw_name_to_filename ────────────────────────────────────────────────────


def test_draw_plain_name_gets_extension():
    assert (
        draw_name_to_filename("2026-05-31-17-00-19") == "2026-05-31-17-00-19.excalidraw"
    )


def test_draw_existing_extension_not_doubled():
    assert (
        draw_name_to_filename("2026-05-31-17-00-19.excalidraw")
        == "2026-05-31-17-00-19.excalidraw"
    )


def test_draw_draws_prefix_is_stripped():
    assert (
        draw_name_to_filename("draws/2026-05-31-17-00-19.excalidraw")
        == "2026-05-31-17-00-19.excalidraw"
    )


def test_draw_name_special_chars_are_encoded():
    assert draw_name_to_filename("a/b") == "a%2Fb.excalidraw"


# ── resolve_draw_path / target_path_for_draw ──────────────────────────────────


def test_target_for_draw_none_when_graph_path_empty():
    assert target_path_for_draw("", "x") is None


def test_target_for_draw_points_into_draws_subdir(tmp_path: Path):
    target = target_path_for_draw(str(tmp_path), "my-draw")
    assert target == (tmp_path / "draws" / "my-draw.excalidraw").resolve()


def test_resolve_draw_returns_none_when_missing(tmp_path: Path):
    (tmp_path / "draws").mkdir()
    assert resolve_draw_path(str(tmp_path), "nope") is None


def test_resolve_draw_finds_existing(tmp_path: Path):
    draws = tmp_path / "draws"
    draws.mkdir()
    target = draws / "2026-05-31-17-00-19.excalidraw"
    target.write_text("{}")
    assert (
        resolve_draw_path(str(tmp_path), "draws/2026-05-31-17-00-19.excalidraw")
        == target.resolve()
    )


def test_resolve_draw_rejects_path_traversal(tmp_path: Path):
    outside = tmp_path.parent / "outside.excalidraw"
    outside.write_text("{}")
    graph = tmp_path / "graph"
    (graph / "draws").mkdir(parents=True)
    assert resolve_draw_path(str(graph), "../outside") is None
