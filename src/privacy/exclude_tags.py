"""Pure tag-based page exclusion logic."""


def extract_tags(properties: dict) -> list[str]:
    """Extract the tags list from a Logseq page properties dict.

    Args:
        properties: Raw properties dict; 'tags' may be a list or comma-string.

    Returns:
        List of tag strings, stripped of surrounding whitespace.

    Complexity: O(T) where T is tag count.
    """
    raw = properties.get("tags", [])
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()]
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    return []


def is_page_excluded(page: dict, exclude_tags: tuple[str, ...]) -> bool:
    """Return True if the page carries any tag in the exclusion tuple.

    Args:
        page: Raw Logseq page dict; may have a 'properties' sub-dict.
        exclude_tags: Tuple of tags to exclude. Empty tuple = no exclusion.

    Returns:
        True when the page should be hidden; False otherwise.

    Complexity: O(T) where T is tag count on the page.
    """
    if not exclude_tags:
        return False
    props = page.get("properties") or {}
    return any(t in exclude_tags for t in extract_tags(props))


def filter_pages(
    pages: list[dict],
    exclude_tags: tuple[str, ...],
) -> list[dict]:
    """Return a new list with excluded pages removed.

    Args:
        pages: Input list (not mutated).
        exclude_tags: Tags causing exclusion.

    Returns:
        New list without excluded pages.

    Complexity: O(N * T) where N is page count, T is max tag count per page.
    """
    if not exclude_tags:
        return list(pages)
    return [p for p in pages if not is_page_excluded(p, exclude_tags)]
