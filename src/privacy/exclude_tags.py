"""Tag-based page exclusion (pure functions; no I/O)."""


def extract_tags(properties: dict) -> list[str]:
    """Return lower-cased tag list from a properties dict.

    Supports three Logseq shapes:
      - list[str]:        ["a", "b"]
      - comma-string:     "a, b"
      - DB-mode list[dict]: [{"name": "a"}, {"name": "b"}]

    @param properties Properties dict; may be empty.
    @returns          List of lower-cased tag strings, possibly empty.
    @complexity O(T) where T is tag count.
    """
    raw = properties.get("tags") if properties else None
    if raw is None:
        return []
    if isinstance(raw, str):
        return [t.strip().lower() for t in raw.split(",") if t.strip()]
    if isinstance(raw, list):
        return [_coerce_tag(t) for t in raw if _coerce_tag(t)]
    return []


def _coerce_tag(value: object) -> str:
    """Lower-case a single tag value regardless of its serialization shape.

    @param value Either a string, a dict with a 'name' key, or anything else (→ "").
    @returns     Lower-cased name string.
    @complexity  O(1).
    """
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, dict):
        name = value.get("name") or value.get("title") or ""
        return str(name).strip().lower()
    return ""


def is_page_excluded(page: dict, exclude_tags: tuple[str, ...]) -> bool:
    """Return True when the page carries any excluded tag.

    @param page         Logseq page dict.
    @param exclude_tags Tuple of tag names; empty → never exclude.
    @returns            Boolean.
    @complexity O(T + E) where T is page tags, E is exclusion list length.
    """
    if not exclude_tags:
        return False
    excluded_lower = {t.lower() for t in exclude_tags}
    page_tags = extract_tags(page.get("properties", {}) or {})
    return any(t in excluded_lower for t in page_tags)


def filter_pages(
    pages: list[dict],
    exclude_tags: tuple[str, ...],
) -> list[dict]:
    """Return a new list with excluded pages removed (input not mutated).

    @complexity O(N * (T + E)) where N is page count.
    """
    if not exclude_tags:
        return list(pages)
    return [p for p in pages if not is_page_excluded(p, exclude_tags)]
