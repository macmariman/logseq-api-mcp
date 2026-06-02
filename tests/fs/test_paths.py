"""Tests for src/fs/paths.py — pure, no mocks."""

from pathlib import Path

from src.fs.paths import (
    detect_name_format,
    draw_name_to_filename,
    page_name_to_filename,
    resolve_draw_path,
    resolve_page_path,
    target_path_for_draw,
    target_path_for_write,
)


def _write_config(graph: Path, body: str) -> None:
    """Create ``<graph>/logseq/config.edn`` with the given body."""
    logseq_dir = graph / "logseq"
    logseq_dir.mkdir(parents=True, exist_ok=True)
    (logseq_dir / "config.edn").write_text(body, encoding="utf-8")


# ── page_name_to_filename ────────────────────────────────────────────────────


def test_plain_name_just_appends_md():
    assert page_name_to_filename("Hello World") == "Hello World.md"


def test_slash_is_url_encoded():
    assert page_name_to_filename("Foo/Bar") == "Foo%2FBar.md"


def test_slash_is_url_encoded_explicit_legacy():
    assert page_name_to_filename("Foo/Bar", "legacy") == "Foo%2FBar.md"


def test_slash_is_triple_lowbar_in_triple_lowbar_format():
    assert page_name_to_filename("Foo/Bar", "triple-lowbar") == "Foo___Bar.md"


def test_triple_lowbar_only_changes_slash():
    # Every other special char is still percent-encoded in triple-lowbar.
    assert page_name_to_filename("a/b#c:d", "triple-lowbar") == "a___b%23c%3Ad.md"


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


def test_resolve_finds_encoded_name_legacy(tmp_path: Path):
    _write_config(tmp_path, ":file/name-format :legacy")
    pages = tmp_path / "pages"
    pages.mkdir()
    target = pages / "Foo%2FBar.md"
    target.write_text("hi")
    assert resolve_page_path(str(tmp_path), "Foo/Bar") == target.resolve()


def test_resolve_finds_triple_lowbar_name(tmp_path: Path):
    # No config.edn → default is triple-lowbar.
    pages = tmp_path / "pages"
    pages.mkdir()
    target = pages / "Foo___Bar.md"
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


# ── detect_name_format ───────────────────────────────────────────────────────


def test_detect_format_defaults_to_triple_lowbar_when_no_config(tmp_path: Path):
    assert detect_name_format(str(tmp_path)) == "triple-lowbar"


def test_detect_format_empty_graph_path_defaults_to_triple_lowbar():
    assert detect_name_format("") == "triple-lowbar"


def test_detect_format_reads_legacy(tmp_path: Path):
    _write_config(tmp_path, "{:file/name-format :legacy}")
    assert detect_name_format(str(tmp_path)) == "legacy"


def test_detect_format_reads_triple_lowbar(tmp_path: Path):
    _write_config(tmp_path, "{:file/name-format :triple-lowbar}")
    assert detect_name_format(str(tmp_path)) == "triple-lowbar"


def test_detect_format_ignores_commented_declaration(tmp_path: Path):
    # The default config ships a commented example; it must not match.
    _write_config(tmp_path, ";;   :file/name-format :legacy\n{}")
    assert detect_name_format(str(tmp_path)) == "triple-lowbar"


def test_detect_format_absent_key_defaults_to_triple_lowbar(tmp_path: Path):
    _write_config(tmp_path, "{:preferred-format :markdown}")
    assert detect_name_format(str(tmp_path)) == "triple-lowbar"


# ── target_path_for_write (namespace formats) ─────────────────────────────────


def test_target_for_write_uses_triple_lowbar_by_default(tmp_path: Path):
    target = target_path_for_write(str(tmp_path), "Kz/CareerPath")
    assert target == (tmp_path / "pages" / "Kz___CareerPath.md").resolve()


def test_target_for_write_uses_legacy_when_configured(tmp_path: Path):
    _write_config(tmp_path, ":file/name-format :legacy")
    target = target_path_for_write(str(tmp_path), "Kz/CareerPath")
    assert target == (tmp_path / "pages" / "Kz%2FCareerPath.md").resolve()


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
