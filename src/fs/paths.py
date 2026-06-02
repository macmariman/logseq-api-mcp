"""Page-name ↔ filesystem-path mapping for file-mode Logseq graphs.

Logseq stores each page as a single ``.md`` file under ``<graph>/pages/``
(or ``<graph>/journals/`` for journal pages). The filename is the page
name with a small set of filesystem-unsafe characters URL-encoded.

This module is pure (no I/O beyond filesystem existence checks) so the
mapping can be unit-tested without a real graph.
"""

import re
from pathlib import Path

# Characters Logseq URL-encodes in filenames. Order matters: ``%`` must be
# encoded first so we don't double-encode the percent signs we introduce.
#
# The mapping for ``/`` depends on the graph's ``:file/name-format`` (see
# ``detect_name_format``): the modern ``:triple-lowbar`` format encodes it as
# ``___`` while the ``:legacy`` format uses ``%2F``. Every *other* character is
# percent-encoded the same way in both formats.
_ENCODE_MAP_LEGACY: tuple[tuple[str, str], ...] = (
    ("%", "%25"),
    ("/", "%2F"),
    ("\\", "%5C"),
    ("#", "%23"),
    (":", "%3A"),
    ("?", "%3F"),
    ("*", "%2A"),
    ('"', "%22"),
    ("<", "%3C"),
    (">", "%3E"),
    ("|", "%7C"),
)

# Triple-lowbar differs from legacy only in how ``/`` is encoded.
_ENCODE_MAP_TRIPLE_LOWBAR: tuple[tuple[str, str], ...] = tuple(
    ("/", "___") if ch == "/" else (ch, repl) for ch, repl in _ENCODE_MAP_LEGACY
)

# Backwards-compatible alias: the legacy map is the historical default.
_ENCODE_MAP = _ENCODE_MAP_LEGACY


def detect_name_format(graph_path: str) -> str:
    """Detect a graph's ``:file/name-format`` from its ``logseq/config.edn``.

    Reads ``<graph>/logseq/config.edn`` and returns the filename format that
    governs how ``/`` is encoded in page filenames:

    - ``"legacy"`` when the file declares ``:file/name-format :legacy``.
    - ``"triple-lowbar"`` when it declares ``:file/name-format :triple-lowbar``
      **or** when the key is absent / the file is missing (Logseq's modern
      default for new graphs).

    Only uncommented declarations count: lines whose first non-space character
    is ``;`` are ignored, so the commented example in the default config does
    not trigger a false match.

    Args:
        graph_path: Absolute path to the graph root.

    Returns:
        ``"legacy"`` or ``"triple-lowbar"``.

    Complexity: O(F) where F is the size of ``config.edn``.
    """
    if not graph_path:
        return "triple-lowbar"

    config_file = Path(graph_path) / "logseq" / "config.edn"
    try:
        text = config_file.read_text(encoding="utf-8")
    except OSError:
        return "triple-lowbar"

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith(";"):
            continue
        match = re.search(r":file/name-format\s+:([a-z-]+)", line)
        if match:
            return "legacy" if match.group(1) == "legacy" else "triple-lowbar"

    return "triple-lowbar"


def page_name_to_filename(page_name: str, name_format: str = "legacy") -> str:
    """Convert a Logseq page name to its on-disk ``.md`` filename.

    Args:
        page_name: Page name as shown in Logseq (e.g. ``"Foo/Bar"``).
        name_format: Either ``"legacy"`` (``/`` → ``%2F``) or
            ``"triple-lowbar"`` (``/`` → ``___``). Defaults to ``"legacy"``.

    Returns:
        The ``.md`` filename Logseq would use (e.g. ``"Foo%2FBar.md"`` in
        legacy mode, ``"Foo___Bar.md"`` in triple-lowbar mode).

    Complexity: O(N) where N is len(page_name).
    """
    encode_map = (
        _ENCODE_MAP_TRIPLE_LOWBAR
        if name_format == "triple-lowbar"
        else _ENCODE_MAP_LEGACY
    )
    encoded = page_name
    for ch, repl in encode_map:
        encoded = encoded.replace(ch, repl)
    return f"{encoded}.md"


def resolve_page_path(graph_path: str, page_name: str) -> Path | None:
    """Resolve a page name to its on-disk path inside ``<graph>``.

    Searches ``pages/`` first, then ``journals/``. Returns the first match
    that exists and resolves inside the graph root. Returns ``None`` if no
    match exists.

    Path traversal is rejected: if the resolved path escapes ``graph_path``
    (e.g. via ``..`` segments) the function returns ``None`` even if the
    target file exists.

    Args:
        graph_path: Absolute path to the graph root.
        page_name: Logseq page name.

    Returns:
        Absolute :class:`Path` to the ``.md`` file, or ``None``.

    Complexity: O(1) filesystem stats.
    """
    if not graph_path:
        return None

    root = Path(graph_path).resolve()
    filename = page_name_to_filename(page_name, detect_name_format(graph_path))

    for subdir in ("pages", "journals"):
        candidate = (root / subdir / filename).resolve()
        # Reject path traversal: candidate must stay inside the graph root.
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        if candidate.is_file():
            return candidate

    return None


# ── Excalidraw draws ─────────────────────────────────────────────────────────
#
# Logseq's ``draw`` command stores each drawing as a single ``.excalidraw``
# file under ``<graph>/draws/``. Pages reference it as a file link:
# ``[[draws/<name>.excalidraw]]``.


def draw_name_to_filename(name: str) -> str:
    """Convert an Excalidraw draw name to its on-disk ``.excalidraw`` filename.

    Accepts the name in any of the forms a user might copy from a page:
    ``"2026-05-31-17-00-19"``, ``"2026-05-31-17-00-19.excalidraw"`` or
    ``"draws/2026-05-31-17-00-19.excalidraw"``. The ``draws/`` prefix and the
    ``.excalidraw`` suffix are stripped before encoding, then the suffix is
    re-appended, so the result is always a bare filename.

    Args:
        name: Draw name as shown in Logseq, with or without the ``draws/``
            prefix and ``.excalidraw`` suffix.

    Returns:
        The ``.excalidraw`` filename Logseq would use.

    Complexity: O(N) where N is len(name).
    """
    stem = name.strip()
    stem = stem.removeprefix("draws/")
    stem = stem.removesuffix(".excalidraw")
    for ch, repl in _ENCODE_MAP:
        stem = stem.replace(ch, repl)
    return f"{stem}.excalidraw"


def resolve_draw_path(graph_path: str, name: str) -> Path | None:
    """Resolve an Excalidraw draw name to its on-disk path inside ``<graph>``.

    Looks only under ``draws/``. Returns the path if the file exists and
    resolves inside the graph root, otherwise ``None``. Path traversal that
    escapes ``graph_path`` is rejected.

    Args:
        graph_path: Absolute path to the graph root.
        name: Draw name (``draws/`` prefix and ``.excalidraw`` suffix optional).

    Returns:
        Absolute :class:`Path` to the ``.excalidraw`` file, or ``None``.

    Complexity: O(1) filesystem stat.
    """
    candidate = target_path_for_draw(graph_path, name)
    if candidate is None or not candidate.is_file():
        return None
    return candidate


def target_path_for_draw(graph_path: str, name: str) -> Path | None:
    """Compute the on-disk target path for *writing* a (possibly new) draw.

    Unlike :func:`resolve_draw_path`, the file need not exist. Path traversal
    that would escape ``graph_path`` is rejected (returns ``None``).

    Args:
        graph_path: Absolute path to the graph root.
        name: Draw name (``draws/`` prefix and ``.excalidraw`` suffix optional).

    Returns:
        Absolute :class:`Path` under ``<graph>/draws/``, or ``None`` on invalid
        input (empty ``graph_path`` or path traversal).
    """
    if not graph_path:
        return None

    root = Path(graph_path).resolve()
    filename = draw_name_to_filename(name)
    candidate = (root / "draws" / filename).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


# Matches Logseq's default journal filename format: ``yyyy_MM_dd``.
# Custom journal formats are not detected; users with non-default config
# can create the file manually once and rely on the overwrite path after.
_JOURNAL_NAME_RE = re.compile(r"^\d{4}_\d{2}_\d{2}$")


def is_journal_name(page_name: str) -> bool:
    """Return True if ``page_name`` matches Logseq's default journal format.

    The default Logseq journal filename is ``yyyy_MM_dd.md``; pages whose
    name (pre-extension) matches that pattern are journal entries.
    """
    return bool(_JOURNAL_NAME_RE.match(page_name))


def target_path_for_write(graph_path: str, page_name: str) -> Path | None:
    """Compute the on-disk target path for *writing* a (possibly new) page.

    Unlike :func:`resolve_page_path`, this does not require the file to
    exist — it picks the subdir based on the page name format:

    - Names matching ``yyyy_MM_dd`` → ``<graph>/journals/<name>.md``
    - Everything else → ``<graph>/pages/<name>.md``

    Path traversal is rejected: if the resolved path would escape
    ``graph_path``, returns ``None``.

    Args:
        graph_path: Absolute path to the graph root.
        page_name: Logseq page name.

    Returns:
        Absolute :class:`Path` for the write target, or ``None`` on invalid
        input (empty ``graph_path`` or path traversal).
    """
    if not graph_path:
        return None

    root = Path(graph_path).resolve()
    filename = page_name_to_filename(page_name, detect_name_format(graph_path))
    subdir = "journals" if is_journal_name(page_name) else "pages"
    candidate = (root / subdir / filename).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate
