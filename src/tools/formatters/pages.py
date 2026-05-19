"""Pure formatters for Logseq page data."""

from datetime import datetime, timezone


def format_timestamp(ts_ms: int | None) -> str:
    """Convert a Logseq millisecond timestamp to a human-readable string.

    Args:
        ts_ms: Timestamp in milliseconds, or None.

    Returns:
        UTC datetime string 'YYYY-MM-DD HH:MM:SS', or 'N/A' if ts_ms is falsy.

    Complexity: O(1).
    """
    if not ts_ms:
        return "N/A"
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_page_entry(page: dict) -> str:
    """Format a single Logseq page dict into a one-line display string.

    Args:
        page: Raw Logseq page dict with id, uuid, originalName, journal?.

    Returns:
        Formatted string with emoji, name, ID, UUID, and timestamps.

    Complexity: O(1).
    """
    is_journal = page.get("journal?", False)
    icon = "📅" if is_journal else "📄"
    name = page.get("originalName") or page.get("name", "<unknown>")
    page_id = page.get("id", "")
    uuid = page.get("uuid", "")
    created = format_timestamp(page.get("createdAt"))
    updated = format_timestamp(page.get("updatedAt"))
    return (
        f"{icon} **{name}**\n"
        f"   ID: {page_id} | UUID: {uuid}\n"
        f"   Created: {created} | Updated: {updated}"
    )


def format_pages_listing(
    pages: list[dict],
    start: int | None = None,
    end: int | None = None,
) -> str:
    """Format a list of Logseq pages into the full pages listing output.

    Args:
        pages: List of raw Logseq page dicts.
        start: Optional slice start index for display note.
        end: Optional slice end index for display note.

    Returns:
        Multi-line formatted string with journal/regular sections.

    Complexity: O(N log N) — sort by name.
    """
    if not pages:
        return "✅ No pages found in Logseq graph"

    sliced = pages[start:end] if (start is not None or end is not None) else pages

    regular = sorted(
        [p for p in sliced if not p.get("journal?", False)],
        key=lambda p: (p.get("originalName") or p.get("name", "")).lower(),
    )
    journals = sorted(
        [p for p in sliced if p.get("journal?", False)],
        key=lambda p: (p.get("originalName") or p.get("name", "")).lower(),
    )

    parts: list[str] = ["📊 **LOGSEQ PAGES LISTING**\n"]

    if start is not None or end is not None:
        parts.append(f"*(showing indices {start}-{end})*\n")

    if regular:
        parts.append(f"## 📄 REGULAR PAGES ({len(regular)})\n")
        parts.extend(format_page_entry(p) + "\n" for p in regular)

    if journals:
        parts.append(f"## 📅 JOURNAL PAGES ({len(journals)})\n")
        parts.extend(format_page_entry(p) + "\n" for p in journals)

    total = len(regular) + len(journals)
    parts.append(f"\n**Total: {total} page(s)**")
    return "\n".join(parts)


def format_namespace_tree(
    pages: list[dict], prefix: str = "", _is_root: bool = True
) -> list[str]:
    """Format a Logseq namespace tree into ASCII tree lines.

    Args:
        pages: Nested page list as returned by getPagesTreeFromNamespace.
        prefix: Current indentation prefix string (accumulated during recursion).
        _is_root: Internal flag; True only for the top-level call.

    Returns:
        List of tree-formatted display lines.

    Complexity: O(N) where N is total node count.
    """
    lines: list[str] = []
    for i, page in enumerate(pages):
        is_last = i == len(pages) - 1
        name = page.get("originalName") or page.get("name", "<unknown>")
        if _is_root:
            lines.append(name)
            child_prefix = ""
        else:
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{name}")
            child_prefix = prefix + ("    " if is_last else "│   ")
        children = page.get("children", [])
        if children:
            lines.extend(format_namespace_tree(children, child_prefix, _is_root=False))
    return lines
