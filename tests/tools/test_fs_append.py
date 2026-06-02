"""Tests for the fs_append tool."""

from pathlib import Path

import pytest

from src.client.config import LogseqConfig
from src.tools.fs_append import _run
from tests.conftest import FakeLogseqClient


def _make_graph(tmp_path: Path) -> Path:
    """Create a minimal graph layout under tmp_path and return its root."""
    (tmp_path / "pages").mkdir()
    (tmp_path / "journals").mkdir()
    return tmp_path


@pytest.mark.asyncio
async def test_append_to_existing_page(tmp_path: Path):
    graph = _make_graph(tmp_path)
    target = graph / "pages" / "Hello.md"
    target.write_text("- old\n")
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "Hello", "- new\n")

    assert "✅" in result[0].text
    assert "Appended" in result[0].text
    assert target.read_text() == "- old\n- new\n"


@pytest.mark.asyncio
async def test_append_inserts_separator_when_no_trailing_newline(tmp_path: Path):
    graph = _make_graph(tmp_path)
    target = graph / "pages" / "NoNL.md"
    target.write_text("- old")  # no trailing newline
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "NoNL", "- new\n")

    assert "✅" in result[0].text
    assert target.read_text() == "- old\n- new\n"


@pytest.mark.asyncio
async def test_append_creates_missing_page_in_pages_subdir(tmp_path: Path):
    graph = _make_graph(tmp_path)
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "Brand New", "- hi\n")

    assert "✅" in result[0].text
    assert "Created" in result[0].text
    assert (graph / "pages" / "Brand New.md").read_text() == "- hi\n"
    assert not (graph / "journals" / "Brand New.md").exists()


@pytest.mark.asyncio
async def test_append_creates_missing_journal_when_name_is_date(tmp_path: Path):
    graph = _make_graph(tmp_path)
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "2026_05_27", "- entry\n")

    assert "✅" in result[0].text
    assert (graph / "journals" / "2026_05_27.md").read_text() == "- entry\n"
    assert not (graph / "pages" / "2026_05_27.md").exists()


@pytest.mark.asyncio
async def test_append_to_existing_journal(tmp_path: Path):
    graph = _make_graph(tmp_path)
    target = graph / "journals" / "2026_05_27.md"
    target.write_text("- morning\n")
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "2026_05_27", "- evening\n")

    assert "✅" in result[0].text
    assert target.read_text() == "- morning\n- evening\n"


@pytest.mark.asyncio
async def test_append_to_empty_file_no_separator(tmp_path: Path):
    graph = _make_graph(tmp_path)
    target = graph / "pages" / "Empty.md"
    target.write_text("")  # empty file
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "Empty", "- first\n")

    assert "✅" in result[0].text
    assert target.read_text() == "- first\n"


@pytest.mark.asyncio
async def test_encoded_name_round_trip(tmp_path: Path):
    """Appending to 'Foo/Bar' lands at pages/Foo___Bar.md (triple-lowbar default)."""
    graph = _make_graph(tmp_path)
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "Foo/Bar", "- nested\n")

    assert "✅" in result[0].text
    assert (graph / "pages" / "Foo___Bar.md").read_text() == "- nested\n"


@pytest.mark.asyncio
async def test_db_mode_refuses(tmp_path: Path):
    graph = _make_graph(tmp_path)
    cfg = LogseqConfig(
        endpoint="http://x", token="t", graph_path=str(graph), db_mode=True
    )

    result = await _run(FakeLogseqClient(), cfg, "Hello", "- x\n")

    assert "❌" in result[0].text
    assert "file-mode" in result[0].text.lower()


@pytest.mark.asyncio
async def test_missing_graph_path_refuses():
    cfg = LogseqConfig(endpoint="http://x", token="t")  # graph_path=""

    result = await _run(FakeLogseqClient(), cfg, "Hello", "- x\n")

    assert "❌" in result[0].text
    assert "LOGSEQ_GRAPH_PATH" in result[0].text


@pytest.mark.asyncio
async def test_handles_exception(tmp_path: Path):
    """A directory at the target path makes open() fail; error is caught."""
    graph = _make_graph(tmp_path)
    # Create a directory where the .md file would live so the append open fails.
    (graph / "pages" / "Hello.md").mkdir()
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "Hello", "- x\n")

    assert "❌" in result[0].text
    assert "Error appending" in result[0].text
