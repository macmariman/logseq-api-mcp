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
_ENCODE_MAP: tuple[tuple[str, str], ...] = (
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


def page_name_to_filename(page_name: str) -> str:
    """Convert a Logseq page name to its on-disk ``.md`` filename.

    Args:
        page_name: Page name as shown in Logseq (e.g. ``"Foo/Bar"``).

    Returns:
        The ``.md`` filename Logseq would use (e.g. ``"Foo%2FBar.md"``).

    Complexity: O(N) where N is len(page_name).
    """
    encoded = page_name
    for ch, repl in _ENCODE_MAP:
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
    filename = page_name_to_filename(page_name)

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
    filename = page_name_to_filename(page_name)
    subdir = "journals" if is_journal_name(page_name) else "pages"
    candidate = (root / subdir / filename).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate
