"""Tests for the fs_read_page tool."""

from pathlib import Path

import pytest

from src.client.config import LogseqConfig
from src.tools.fs_read_page import _run
from tests.conftest import FakeLogseqClient


def _make_graph(tmp_path: Path) -> Path:
    """Create a minimal graph layout under tmp_path and return its root."""
    (tmp_path / "pages").mkdir()
    (tmp_path / "journals").mkdir()
    return tmp_path


@pytest.mark.asyncio
async def test_happy_path_reads_raw_markdown(tmp_path: Path):
    graph = _make_graph(tmp_path)
    body = "- block one\n- block two\n"
    (graph / "pages" / "Hello.md").write_text(body)
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "Hello")
    text = result[0].text

    assert body in text
    assert "Hello" in text
    assert "pages/Hello.md" in text
    assert "bytes" in text


@pytest.mark.asyncio
async def test_finds_page_with_encoded_name(tmp_path: Path):
    graph = _make_graph(tmp_path)
    (graph / "pages" / "Foo%2FBar.md").write_text("nested\n")
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "Foo/Bar")
    assert "nested" in result[0].text


@pytest.mark.asyncio
async def test_missing_page_returns_error(tmp_path: Path):
    graph = _make_graph(tmp_path)
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "Nope")
    assert "❌" in result[0].text
    assert "not found" in result[0].text.lower()


@pytest.mark.asyncio
async def test_db_mode_refuses(tmp_path: Path):
    graph = _make_graph(tmp_path)
    cfg = LogseqConfig(
        endpoint="http://x", token="t", graph_path=str(graph), db_mode=True
    )

    result = await _run(FakeLogseqClient(), cfg, "Hello")
    assert "❌" in result[0].text
    assert "file-mode" in result[0].text.lower()


@pytest.mark.asyncio
async def test_missing_graph_path_returns_error():
    cfg = LogseqConfig(endpoint="http://x", token="t")  # graph_path defaults to ""

    result = await _run(FakeLogseqClient(), cfg, "Hello")
    assert "❌" in result[0].text
    assert "LOGSEQ_GRAPH_PATH" in result[0].text


@pytest.mark.asyncio
async def test_path_traversal_returns_not_found(tmp_path: Path):
    graph = _make_graph(tmp_path)
    # Plant a file outside the graph that we'd never want to read.
    (tmp_path.parent / "secret.md").write_text("nope")
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "../secret")
    assert "❌" in result[0].text
    assert "not found" in result[0].text.lower()
