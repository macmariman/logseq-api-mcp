"""Skill documentation integrity.

The `.claude/skills/logseq` skill is plain markdown, so it has no runtime
behavior to unit-test. What *can* drift silently is its consistency with the
code and with itself:

1. Every tool name the skill documents must still exist in ``tools.__all__``
   (catches renames/removals that leave the docs pointing at a dead tool).
2. Every internal ``*.md`` cross-reference must resolve to a real file
   (catches renamed/moved reference files that break navigation).

These checks keep the docs honest without any new dependency.
"""

import re
from pathlib import Path

from src import tools

_SKILL_ROOT = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "logseq"

# Inline-code span: anything between single backticks.
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")

# A tool-like identifier: lowercase words joined by underscores (e.g.
# ``get_linked_references``). Single words such as ``search``/``query`` are
# intentionally NOT matched — they overlap with prose and can't be told apart
# from ordinary backticked words.
_TOOL_IDENT_RE = re.compile(r"\b[a-z]+(?:_[a-z]+)+\b")

# Lowercase identifiers with underscores that appear in the skill but are not
# MCP tools. Keep this list tight and documented.
_NON_TOOL_IDENTIFIERS: frozenset[str] = frozenset(
    {
        # Filename / format tokens.
        "yyyy_mm_dd",  # journal filename format
        "render_excalidraw",  # local Playwright script (render_excalidraw.py)
        # Tool *parameter* names (documented inline, not tools themselves).
        "since_days",
        "include_namespace_children",
        "include_content",
    }
)

# A ``.md`` cross-reference worth validating: either an explicit path under
# ``references/`` or a bare skill-style filename (lowercase + hyphens). This
# deliberately excludes *example* filenames in the docs (dates like
# ``2026_05_31.md``, encoded names like ``Area___Topic.md``).
_DOC_REF_RE = re.compile(r"(references/[\w./-]+\.md|\b[a-z][a-z-]*\.md)")


def _skill_md_files() -> list[Path]:
    files = sorted(_SKILL_ROOT.rglob("*.md"))
    assert files, f"No skill markdown found under {_SKILL_ROOT}"
    return files


def _read_all_skill_text() -> dict[Path, str]:
    return {p: p.read_text(encoding="utf-8") for p in _skill_md_files()}


def test_documented_tool_names_exist() -> None:
    """Every tool-shaped identifier in the skill must be a real MCP tool."""
    valid = set(tools.__all__)
    offenders: dict[str, list[str]] = {}

    for path, text in _read_all_skill_text().items():
        for span in _INLINE_CODE_RE.findall(text):
            for ident in _TOOL_IDENT_RE.findall(span):
                if ident in _NON_TOOL_IDENTIFIERS or ident in valid:
                    continue
                offenders.setdefault(ident, []).append(path.name)

    assert not offenders, (
        "Skill docs reference tool-shaped identifiers that are not in "
        f"tools.__all__ (rename in code or fix the docs): {offenders}"
    )


def test_internal_md_references_resolve() -> None:
    """Every internal ``*.md`` cross-reference must point at a real file."""
    available = {p.name for p in _skill_md_files()}
    missing: dict[str, list[str]] = {}

    for path, text in _read_all_skill_text().items():
        for ref in _DOC_REF_RE.findall(text):
            if "/" in ref:
                # Path relative to the skill root (e.g. references/.../x.md).
                target = (_SKILL_ROOT / ref).resolve()
                exists = target.is_file()
            else:
                # Bare filename: must exist somewhere under the skill root.
                exists = ref in available
            if not exists:
                missing.setdefault(ref, []).append(path.name)

    assert not missing, (
        "Skill docs reference markdown files that do not exist "
        f"(renamed/moved/typo): {missing}"
    )
