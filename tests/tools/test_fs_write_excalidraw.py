"""Tests for the fs_write_excalidraw tool."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.client.config import LogseqConfig
from src.tools.fs_write_excalidraw import _run
from tests.conftest import FakeLogseqClient


def _make_graph(tmp_path: Path) -> Path:
    (tmp_path / "draws").mkdir()
    return tmp_path


def _cfg(graph: Path, **kw) -> LogseqConfig:
    return LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph), **kw)


def _scene_json(**extra) -> str:
    return json.dumps({"type": "excalidraw", "version": 2, "elements": [], **extra})


@pytest.mark.asyncio
async def test_create_new_drawing(tmp_path: Path):
    graph = _make_graph(tmp_path)
    result = await _run(FakeLogseqClient(), _cfg(graph), "new", _scene_json(), "create")

    text = result[0].text
    assert "✅" in text and "Created" in text
    assert "new.excalidraw" in text
    assert "[[draws/new.excalidraw]]" in text
    written = json.loads((graph / "draws" / "new.excalidraw").read_text())
    assert written["type"] == "excalidraw"


@pytest.mark.asyncio
async def test_create_from_elements_only_fills_defaults(tmp_path: Path):
    graph = _make_graph(tmp_path)
    content = json.dumps({"elements": [{"type": "text", "text": "hi"}]})

    result = await _run(FakeLogseqClient(), _cfg(graph), "scratch", content, "create")

    assert "✅" in result[0].text
    written = json.loads((graph / "draws" / "scratch.excalidraw").read_text())
    assert written["type"] == "excalidraw"
    assert written["version"] == 2
    assert written["source"] == "logseq-api-mcp"
    assert written["appState"] == {} and written["files"] == {}
    assert written["elements"][0]["text"] == "hi"


@pytest.mark.asyncio
async def test_overwrite_existing(tmp_path: Path):
    graph = _make_graph(tmp_path)
    target = graph / "draws" / "d.excalidraw"
    target.write_text(_scene_json())

    new = _scene_json(elements=[{"type": "rectangle"}])
    result = await _run(FakeLogseqClient(), _cfg(graph), "d", new, "overwrite")

    assert "✅" in result[0].text and "Overwritten" in result[0].text
    assert json.loads(target.read_text())["elements"] == [{"type": "rectangle"}]


@pytest.mark.asyncio
async def test_create_fails_when_exists(tmp_path: Path):
    graph = _make_graph(tmp_path)
    target = graph / "draws" / "d.excalidraw"
    target.write_text(_scene_json())

    result = await _run(FakeLogseqClient(), _cfg(graph), "d", _scene_json(), "create")
    assert "❌" in result[0].text and "already exists" in result[0].text.lower()


@pytest.mark.asyncio
async def test_overwrite_fails_when_missing(tmp_path: Path):
    graph = _make_graph(tmp_path)
    result = await _run(
        FakeLogseqClient(), _cfg(graph), "ghost", _scene_json(), "overwrite"
    )
    assert "❌" in result[0].text and "not found" in result[0].text.lower()


@pytest.mark.asyncio
async def test_upsert_creates_then_overwrites(tmp_path: Path):
    graph = _make_graph(tmp_path)
    cfg = _cfg(graph)

    r1 = await _run(FakeLogseqClient(), cfg, "u", _scene_json(), "upsert")
    assert "Created" in r1[0].text
    r2 = await _run(FakeLogseqClient(), cfg, "u", _scene_json(), "upsert")
    assert "Overwritten" in r2[0].text


@pytest.mark.asyncio
async def test_invalid_json_rejected(tmp_path: Path):
    graph = _make_graph(tmp_path)
    result = await _run(FakeLogseqClient(), _cfg(graph), "x", "{not json", "create")
    assert "❌" in result[0].text and "not valid JSON" in result[0].text


@pytest.mark.asyncio
async def test_missing_elements_rejected(tmp_path: Path):
    graph = _make_graph(tmp_path)
    result = await _run(FakeLogseqClient(), _cfg(graph), "x", json.dumps({}), "create")
    assert "❌" in result[0].text and "elements" in result[0].text


@pytest.mark.asyncio
async def test_wrong_type_rejected(tmp_path: Path):
    graph = _make_graph(tmp_path)
    content = json.dumps({"type": "drawio", "elements": []})
    result = await _run(FakeLogseqClient(), _cfg(graph), "x", content, "create")
    assert "❌" in result[0].text and "expected 'excalidraw'" in result[0].text


@pytest.mark.asyncio
async def test_invalid_mode(tmp_path: Path):
    graph = _make_graph(tmp_path)
    result = await _run(FakeLogseqClient(), _cfg(graph), "x", _scene_json(), "bogus")  # type: ignore[arg-type]
    assert "❌" in result[0].text and "invalid mode" in result[0].text.lower()


@pytest.mark.asyncio
async def test_db_mode_refuses(tmp_path: Path):
    graph = _make_graph(tmp_path)
    result = await _run(
        FakeLogseqClient(), _cfg(graph, db_mode=True), "x", _scene_json(), "upsert"
    )
    assert "❌" in result[0].text and "file-mode" in result[0].text.lower()


@pytest.mark.asyncio
async def test_missing_graph_path_refuses():
    cfg = LogseqConfig(endpoint="http://x", token="t")
    result = await _run(FakeLogseqClient(), cfg, "x", _scene_json(), "upsert")
    assert "❌" in result[0].text and "LOGSEQ_GRAPH_PATH" in result[0].text


@pytest.mark.asyncio
async def test_write_is_atomic_no_partial_on_failure(tmp_path: Path):
    graph = _make_graph(tmp_path)
    target = graph / "draws" / "d.excalidraw"
    target.write_text(_scene_json(source="original"))

    with patch(
        "src.tools.fs_write_excalidraw.os.replace", side_effect=OSError("disk full")
    ):
        result = await _run(
            FakeLogseqClient(), _cfg(graph), "d", _scene_json(source="new"), "overwrite"
        )

    assert "❌" in result[0].text
    assert json.loads(target.read_text())["source"] == "original"  # untouched
    leftovers = [
        p for p in (graph / "draws").iterdir() if p.name.startswith(".d.excalidraw")
    ]
    assert leftovers == [], f"tempfile leaked: {leftovers}"
