"""Write a Logseq Excalidraw drawing directly to disk (file-mode graphs only).

Atomically creates or overwrites a ``.excalidraw`` file under
``<graph>/draws/``. The input is the Excalidraw *scene* JSON; the tool
validates it, fills in any missing top-level scaffolding fields with safe
defaults (so a scene can be created from just an ``elements`` array), and
re-serializes it canonically.

It does **not** touch any page. After writing, it returns the bare filename so
the caller can insert ``[[draws/<filename>]]`` into a page via fs_write_page or
a normal block edit.

Atomicity follows the same tempfile + ``os.replace`` strategy as
fs_write_page: a failed write leaves the original file untouched.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, List, Literal

from mcp.types import TextContent

from src.client.config import LogseqConfig
from src.client.logseq_client import LogseqClient
from src.fs.paths import draw_name_to_filename, resolve_draw_path, target_path_for_draw
from src.logging_setup import get_logger

_log = get_logger(__name__)

WriteMode = Literal["create", "overwrite", "upsert"]

# Default top-level scaffolding for an Excalidraw scene. Logseq writes these
# fields; we fill any that the caller omits so a drawing can be created from
# just an `elements` list.
_SCENE_DEFAULTS: dict[str, Any] = {
    "type": "excalidraw",
    "version": 2,
    "source": "logseq-api-mcp",
    "appState": {},
    "files": {},
}


def _atomic_write(target: Path, content: str) -> None:
    """Write ``content`` to ``target`` atomically via tempfile + os.replace.

    The tempfile is created in the same directory as ``target`` so the final
    rename stays on one filesystem. On any error the tempfile is cleaned up and
    the original target is left intact.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
    )
    tmp = Path(tmp_path)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp, target)
    except BaseException:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise


def _normalize_scene(content: str) -> tuple[str | None, str]:
    """Validate and canonicalize an Excalidraw scene.

    Args:
        content: Raw JSON string for the scene (or at least an object with an
            ``elements`` array).

    Returns:
        ``(canonical_json, "")`` on success, or ``(None, error_message)`` if
        the input is not a valid Excalidraw scene.
    """
    try:
        scene = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, f"content is not valid JSON: {exc}"

    if not isinstance(scene, dict):
        return None, "scene must be a JSON object with an 'elements' array."

    elements = scene.get("elements")
    if not isinstance(elements, list):
        return None, "scene must contain an 'elements' array."

    declared_type = scene.get("type")
    if declared_type is not None and declared_type != "excalidraw":
        return None, f"unexpected scene type {declared_type!r}; expected 'excalidraw'."

    merged = {**_SCENE_DEFAULTS, **scene}
    return json.dumps(merged, indent=2, ensure_ascii=False), ""


async def _run(
    client: LogseqClient,
    config: LogseqConfig,
    name: str,
    content: str,
    mode: WriteMode = "overwrite",
) -> List[TextContent]:
    """Write an Excalidraw drawing to disk atomically.

    Args:
        client: Unused; kept for the standard tool signature.
        config: Provides ``graph_path`` and ``db_mode``.
        name: Draw name (``draws/`` prefix and ``.excalidraw`` suffix optional).
        content: Excalidraw scene JSON. Missing top-level fields (type,
            version, source, appState, files) are filled with defaults.
        mode: ``"create"`` fails if the drawing exists, ``"overwrite"``
            (default) fails if it does not, ``"upsert"`` accepts both.

    Returns:
        Single :class:`TextContent` with the bare ``.excalidraw`` filename and
        a ready-to-paste ``[[draws/...]]`` reference. On error, a
        ``❌``-prefixed message.

    Complexity: O(N) where N is len(content).
    """
    try:
        _log.debug("%s called: %r mode=%s", __name__, name, mode)

        if config.db_mode:
            return [
                TextContent(
                    type="text",
                    text="❌ fs_write_excalidraw is for file-mode graphs only "
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

        if mode not in ("create", "overwrite", "upsert"):
            return [
                TextContent(
                    type="text",
                    text=f"❌ Invalid mode {mode!r}. "
                    "Must be 'create', 'overwrite', or 'upsert'.",
                )
            ]

        canonical, err = _normalize_scene(content)
        if canonical is None:
            return [
                TextContent(type="text", text=f"❌ Invalid Excalidraw scene: {err}")
            ]

        existing = resolve_draw_path(config.graph_path, name)

        if mode == "create" and existing is not None:
            return [
                TextContent(
                    type="text",
                    text=(
                        f"❌ Drawing already exists: {name!r} (at {existing}). "
                        "Use mode='overwrite' or 'upsert'."
                    ),
                )
            ]
        if mode == "overwrite" and existing is None:
            return [
                TextContent(
                    type="text",
                    text=(
                        f"❌ Drawing not found: {name!r} (searched draws/). "
                        "Use mode='create' or 'upsert' to create it."
                    ),
                )
            ]

        if existing is not None:
            target = existing
            action = "overwritten"
        else:
            candidate = target_path_for_draw(config.graph_path, name)
            if candidate is None:
                return [
                    TextContent(
                        type="text",
                        text=f"❌ Refusing to write outside graph root: {name!r}.",
                    )
                ]
            target = candidate
            action = "created"

        _atomic_write(target, canonical)

        filename = draw_name_to_filename(name)
        size = len(canonical.encode("utf-8"))
        return [
            TextContent(
                type="text",
                text=(
                    f"✅ {action.capitalize()} drawing ({size} bytes)\n"
                    f"📄 {filename}\n"
                    f"🔗 Reference: [[draws/{filename}]]"
                ),
            )
        ]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [TextContent(type="text", text=f"❌ Error writing drawing: {exc}")]


async def fs_write_excalidraw(
    client: LogseqClient,
    config: LogseqConfig,
    name: str,
    content: str,
    mode: WriteMode = "overwrite",
) -> List[TextContent]:
    """Atomically write a Logseq Excalidraw drawing to disk (file-mode graphs only).

    The drawing is written under draws/; no page is modified. The tool returns
    the bare filename and a [[draws/...]] reference you can insert into a page
    with fs_write_page or a normal block edit.

    Args:
        name: Draw name, e.g. "2026-05-31-17-00-19" (the draws/ prefix and
            .excalidraw suffix are optional).
        content: Excalidraw scene JSON. At minimum an object with an
            "elements" array; missing top-level fields (type, version, source,
            appState, files) are filled with sensible defaults. To edit an
            existing drawing, read it with fs_read_excalidraw, modify the JSON,
            and write it back.
        mode: "create" fails if the drawing exists; "overwrite" (default)
            fails if it doesn't; "upsert" accepts both.
    """
    # client/config are injected by the registry's adaptive binding.
    return await _run(client, config, name, content, mode)
