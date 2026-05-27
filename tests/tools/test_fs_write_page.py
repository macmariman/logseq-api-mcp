"""Tests for the fs_write_page tool."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.client.config import LogseqConfig
from src.tools.fs_write_page import _run
from tests.conftest import FakeLogseqClient


def _make_graph(tmp_path: Path) -> Path:
    """Create a minimal graph layout under tmp_path and return its root."""
    (tmp_path / "pages").mkdir()
    (tmp_path / "journals").mkdir()
    return tmp_path


@pytest.mark.asyncio
async def test_overwrite_existing_page(tmp_path: Path):
    graph = _make_graph(tmp_path)
    target = graph / "pages" / "Hello.md"
    target.write_text("- old\n")
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "Hello", "- new\n", mode="overwrite")

    assert "✅" in result[0].text
    assert "Overwritten" in result[0].text
    assert target.read_text() == "- new\n"


@pytest.mark.asyncio
async def test_overwrite_existing_journal_in_journals_subdir(tmp_path: Path):
    """If a file already lives in journals/, we overwrite it there regardless of name."""
    graph = _make_graph(tmp_path)
    # Non-date name placed in journals/ — exotic but legal in Logseq.
    target = graph / "journals" / "MyNote.md"
    target.write_text("- old\n")
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "MyNote", "- new\n", mode="overwrite")

    assert "✅" in result[0].text
    assert target.read_text() == "- new\n"
    # And the pages/ subdir must NOT have been touched.
    assert not (graph / "pages" / "MyNote.md").exists()


@pytest.mark.asyncio
async def test_create_new_page_goes_to_pages_subdir(tmp_path: Path):
    graph = _make_graph(tmp_path)
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "Brand New", "- hi\n", mode="create")

    assert "✅" in result[0].text
    assert "Created" in result[0].text
    assert (graph / "pages" / "Brand New.md").read_text() == "- hi\n"
    assert not (graph / "journals" / "Brand New.md").exists()


@pytest.mark.asyncio
async def test_create_new_journal_when_name_is_date(tmp_path: Path):
    graph = _make_graph(tmp_path)
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(
        FakeLogseqClient(), cfg, "2026_05_27", "- entry\n", mode="create"
    )

    assert "✅" in result[0].text
    assert (graph / "journals" / "2026_05_27.md").read_text() == "- entry\n"
    assert not (graph / "pages" / "2026_05_27.md").exists()


@pytest.mark.asyncio
async def test_upsert_creates_if_missing(tmp_path: Path):
    graph = _make_graph(tmp_path)
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "NewOne", "- x\n", mode="upsert")

    assert "✅" in result[0].text
    assert "Created" in result[0].text
    assert (graph / "pages" / "NewOne.md").read_text() == "- x\n"


@pytest.mark.asyncio
async def test_upsert_overwrites_if_exists(tmp_path: Path):
    graph = _make_graph(tmp_path)
    target = graph / "pages" / "Existing.md"
    target.write_text("- old\n")
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "Existing", "- new\n", mode="upsert")

    assert "✅" in result[0].text
    assert "Overwritten" in result[0].text
    assert target.read_text() == "- new\n"


@pytest.mark.asyncio
async def test_mode_create_fails_when_exists(tmp_path: Path):
    graph = _make_graph(tmp_path)
    target = graph / "pages" / "Exists.md"
    target.write_text("- keep\n")
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "Exists", "- new\n", mode="create")

    assert "❌" in result[0].text
    assert "already exists" in result[0].text.lower()
    assert target.read_text() == "- keep\n"  # untouched


@pytest.mark.asyncio
async def test_mode_overwrite_fails_when_missing(tmp_path: Path):
    graph = _make_graph(tmp_path)
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "Nope", "- x\n", mode="overwrite")

    assert "❌" in result[0].text
    assert "not found" in result[0].text.lower()
    assert not (graph / "pages" / "Nope.md").exists()


@pytest.mark.asyncio
async def test_invalid_mode_returns_error(tmp_path: Path):
    graph = _make_graph(tmp_path)
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "X", "- x\n", mode="bogus")  # type: ignore[arg-type]

    assert "❌" in result[0].text
    assert "invalid mode" in result[0].text.lower()


@pytest.mark.asyncio
async def test_traversal_attempt_is_neutralized_by_encoding(tmp_path: Path):
    """Slashes in page names are URL-encoded, so traversal collapses to a flat name."""
    graph = _make_graph(tmp_path)
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "../escape", "- evil\n", mode="upsert")

    # Write succeeds but the filename is encoded — file stays inside pages/.
    assert "✅" in result[0].text
    assert (graph / "pages" / "..%2Fescape.md").exists()
    # Nothing escapes the graph root.
    assert not (tmp_path.parent / "escape.md").exists()
    assert not (tmp_path / "escape.md").exists()


@pytest.mark.asyncio
async def test_db_mode_refuses(tmp_path: Path):
    graph = _make_graph(tmp_path)
    cfg = LogseqConfig(
        endpoint="http://x", token="t", graph_path=str(graph), db_mode=True
    )

    result = await _run(FakeLogseqClient(), cfg, "Hello", "- x\n", mode="upsert")

    assert "❌" in result[0].text
    assert "file-mode" in result[0].text.lower()


@pytest.mark.asyncio
async def test_missing_graph_path_refuses():
    cfg = LogseqConfig(endpoint="http://x", token="t")  # graph_path=""

    result = await _run(FakeLogseqClient(), cfg, "Hello", "- x\n", mode="upsert")

    assert "❌" in result[0].text
    assert "LOGSEQ_GRAPH_PATH" in result[0].text


@pytest.mark.asyncio
async def test_write_is_atomic_no_partial_on_failure(tmp_path: Path):
    """If os.replace fails, the target is unchanged and no .tmp file remains."""
    graph = _make_graph(tmp_path)
    target = graph / "pages" / "Atomic.md"
    target.write_text("- original\n")
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    with patch("src.tools.fs_write_page.os.replace", side_effect=OSError("disk full")):
        result = await _run(
            FakeLogseqClient(), cfg, "Atomic", "- new\n", mode="overwrite"
        )

    assert "❌" in result[0].text
    assert target.read_text() == "- original\n"  # untouched
    # No leftover tempfiles in the pages dir.
    leftovers = [
        p for p in (graph / "pages").iterdir() if p.name.startswith(".Atomic.md")
    ]
    assert leftovers == [], f"tempfile leaked: {leftovers}"


@pytest.mark.asyncio
async def test_encoded_name_round_trip(tmp_path: Path):
    """Writing 'Foo/Bar' lands at pages/Foo%2FBar.md."""
    graph = _make_graph(tmp_path)
    cfg = LogseqConfig(endpoint="http://x", token="t", graph_path=str(graph))

    result = await _run(FakeLogseqClient(), cfg, "Foo/Bar", "- nested\n", mode="create")

    assert "✅" in result[0].text
    assert (graph / "pages" / "Foo%2FBar.md").read_text() == "- nested\n"
