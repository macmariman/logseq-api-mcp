"""Read a Logseq Excalidraw drawing directly from disk (file-mode graphs only).

Logseq's ``draw`` command stores each drawing as an ``.excalidraw`` file (a
JSON Excalidraw *scene*) under ``<graph>/draws/`` and references it from a page
as ``[[draws/<name>.excalidraw]]``.

This tool returns a short, human-readable summary of the scene (element counts
by type plus every text label found) followed by the raw JSON, so the model can
both understand the drawing and edit it for a round-trip via
``fs_write_excalidraw``.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any, List

from mcp.types import TextContent

from src.client.config import LogseqConfig
from src.client.logseq_client import LogseqClient
from src.fs.paths import resolve_draw_path
from src.logging_setup import get_logger

_log = get_logger(__name__)


def _summarize(scene: dict[str, Any]) -> str:
    """Build a human-readable summary of an Excalidraw scene.

    Counts elements by ``type`` (skipping deleted ones) and collects the text
    of every textual element so the caller can read the drawing's labels
    without parsing geometry.
    """
    elements = scene.get("elements") or []
    type_counts: Counter[str] = Counter()
    texts: list[str] = []
    for el in elements:
        if not isinstance(el, dict) or el.get("isDeleted"):
            continue
        type_counts[str(el.get("type", "unknown"))] += 1
        text = el.get("text")
        if isinstance(text, str) and text.strip():
            texts.append(text.strip())

    live = sum(type_counts.values())
    by_type = ", ".join(f"{t}×{n}" for t, n in sorted(type_counts.items())) or "none"
    lines = [f"🎨 {live} elements ({by_type})"]
    if texts:
        lines.append("📝 Text:")
        lines.extend(f"  • {t}" for t in texts)
    return "\n".join(lines)


async def _run(
    client: LogseqClient,
    config: LogseqConfig,
    name: str,
) -> List[TextContent]:
    """Read an Excalidraw drawing from disk and return summary + raw JSON.

    Args:
        client: Unused; kept for the standard tool signature so the registry
            can inject the shared client uniformly.
        config: Provides ``graph_path`` and ``db_mode``.
        name: Draw name as referenced in Logseq. The ``draws/`` prefix and
            ``.excalidraw`` suffix are optional.

    Returns:
        List with one :class:`TextContent`: a header (name, relative path) and
        a summary, followed by the raw JSON scene. On error, a single
        ``❌``-prefixed message.

    Complexity: O(E) where E is the number of elements in the scene.
    """
    try:
        _log.debug("%s called: %r", __name__, name)

        if config.db_mode:
            return [
                TextContent(
                    type="text",
                    text="❌ fs_read_excalidraw is for file-mode graphs only "
                    "(LOGSEQ_DB_MODE=true is set).",
                )
            ]

        if not config.graph_path:
            return [
                TextContent(
                    type="text",
                    text="❌ LOGSEQ_GRAPH_PATH is not set. Point it at your "
                    "graph root (the folder containing pages/ and journals/).",
                )
            ]

        path = resolve_draw_path(config.graph_path, name)
        if path is None:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Drawing not found: {name!r} (searched draws/).",
                )
            ]

        raw = path.read_text(encoding="utf-8")
        rel = path.relative_to(Path(config.graph_path).resolve())

        try:
            scene = json.loads(raw)
            summary = _summarize(scene) if isinstance(scene, dict) else "(not a scene)"
        except json.JSONDecodeError as exc:
            summary = f"⚠️ File is not valid JSON: {exc}"

        header = f"🖼️ {name}\n📁 {rel}\n{summary}\n\n---\n\n"
        return [TextContent(type="text", text=header + raw)]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error reading drawing: {exc}")]


async def fs_read_excalidraw(
    client: LogseqClient,
    config: LogseqConfig,
    name: str,
) -> List[TextContent]:
    """Read a Logseq Excalidraw drawing from disk (file-mode graphs only).

    Returns a summary (element counts + text labels) plus the raw JSON scene,
    which you can edit and write back with fs_write_excalidraw.

    Args:
        name: Draw name as referenced in Logseq, e.g.
            "2026-05-31-17-00-19", "2026-05-31-17-00-19.excalidraw", or
            "draws/2026-05-31-17-00-19.excalidraw". The prefix/suffix are
            optional.
    """
    # client/config are injected by the registry's adaptive binding.
    return await _run(client, config, name)
