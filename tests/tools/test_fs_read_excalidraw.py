"""Tests for the fs_read_excalidraw tool."""

import json
from pathlib import Path

import pytest

from src.client.config import LogseqConfig
from src.tools.fs_read_excalidraw import _run
from tests.conftest import FakeLogseqClient

_SCENE = {
    "type": "excalidraw",
    "version": 2,
    "source": "logseq",
    "elements": [
        {"type": "rectangle", "id": "a"},
        {"type": "arrow", "id": "b"},
        {"type": "text", "id": "c", "text": "Hello"},
        {"type": "text", "id": "d", "text": "World", "isDeleted": True},
    ],
    "appState": {},
    "files": {},
}


def _make_graph(tmp_path: Path) -> Path:
    (tmp_path / "draws").mkdir()
    return tmp_path


def _cfg(graph: Path, **kw) -> LogseqConfig:
    return LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph), **kw)


@pytest.mark.asyncio
async def test_reads_summary_and_raw(tmp_path: Path):
    graph = _make_graph(tmp_path)
    raw = json.dumps(_SCENE)
    (graph / "draws" / "drawing.excalidraw").write_text(raw)

    result = await _run(FakeLogseqClient(), _cfg(graph), "drawing")

    text = result[0].text
    # Summary: 3 live elements (deleted text excluded), counts, and text label.
    assert "🎨 3 elements" in text
    assert "rectangle×1" in text and "arrow×1" in text and "text×1" in text
    assert "Hello" in text
    assert "World" not in text.split("---")[0]  # deleted element not summarized
    # Raw JSON is appended after the divider.
    assert raw in text


@pytest.mark.asyncio
async def test_accepts_full_reference_form(tmp_path: Path):
    graph = _make_graph(tmp_path)
    (graph / "draws" / "drawing.excalidraw").write_text(json.dumps(_SCENE))

    result = await _run(FakeLogseqClient(), _cfg(graph), "draws/drawing.excalidraw")
    assert "🎨" in result[0].text


@pytest.mark.asyncio
async def test_not_found(tmp_path: Path):
    graph = _make_graph(tmp_path)
    result = await _run(FakeLogseqClient(), _cfg(graph), "missing")
    assert "❌" in result[0].text
    assert "not found" in result[0].text.lower()


@pytest.mark.asyncio
async def test_invalid_json_still_returns_raw(tmp_path: Path):
    graph = _make_graph(tmp_path)
    (graph / "draws" / "broken.excalidraw").write_text("{not json")

    result = await _run(FakeLogseqClient(), _cfg(graph), "broken")
    assert "not valid JSON" in result[0].text
    assert "{not json" in result[0].text


@pytest.mark.asyncio
async def test_db_mode_refuses(tmp_path: Path):
    graph = _make_graph(tmp_path)
    result = await _run(FakeLogseqClient(), _cfg(graph, db_mode=True), "drawing")
    assert "❌" in result[0].text
    assert "file-mode" in result[0].text.lower()


@pytest.mark.asyncio
async def test_missing_graph_path_refuses():
    cfg = LogseqConfig(endpoint="http://x", token="t")
    result = await _run(FakeLogseqClient(), cfg, "drawing")
    assert "❌" in result[0].text
    assert "LOGSEQ_GRAPH_PATH" in result[0].text
