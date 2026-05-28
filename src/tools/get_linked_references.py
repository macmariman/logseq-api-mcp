"""Programmatic equivalent of Logseq's "Linked References" right-side panel.

Returns every block across the graph that references a given page, together
with each block's full nested subtree, grouped by source page. Supports
filtering by recency (filesystem mtime), a result cap, and namespace
descendants.

Implementation note: ``logseq.Editor.getPageLinkedReferences`` returns
linking *pages* (not the matching blocks themselves) — confirmed in the
wild against a real graph. To recover the actual referencing blocks with
their subtrees, we fetch each linking page's full block tree and walk it
looking for ``[[tag]]`` in block content. This mirrors what
``get_linked_flashcards`` does for ``#card`` markers.
"""

import datetime
import re
from pathlib import Path
from typing import List

from mcp.types import TextContent

from src.client.config import LogseqConfig
from src.client.logseq_client import LogseqClient
from src.fs.paths import resolve_page_path
from src.logging_setup import get_logger
from src.tools.formatters.blocks import format_block_tree

_log = get_logger(__name__)

_SECONDS_PER_DAY = 86400

# Logseq returns journal pages by their display name (e.g. "Jan 22nd, 2026"),
# but the file on disk uses ``YYYY_MM_DD.md``. To stat the file for mtime we
# need to translate the display name back to the filename. Covers the default
# English locale Logseq ships with; users with custom journal formats can fall
# through to ``resolve_page_path`` directly.
_JOURNAL_DISPLAY_RE = re.compile(
    r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
    r"(\d{1,2})(?:st|nd|rd|th), (\d{4})$"
)
_MONTH_TO_NUM = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
}  # fmt: skip


def _journal_display_to_filename(display_name: str) -> str | None:
    """Convert a journal display name to its ``YYYY_MM_DD`` filename stem.

    Returns ``None`` for non-journal names or non-default formats.
    """
    m = _JOURNAL_DISPLAY_RE.match(display_name)
    if not m:
        return None
    month, day, year = m.groups()
    return f"{year}_{_MONTH_TO_NUM[month]}_{int(day):02d}"


def _resolve_page_mtime(graph_path: str, page_name: str) -> float:
    """Return the mtime of a page's .md file, or 0.0 if it cannot be located.

    Tries the page name as-is first (covers regular pages); if that misses,
    falls back to parsing a default-format journal display name and stating
    ``journals/<YYYY_MM_DD>.md``.
    """
    path = resolve_page_path(graph_path, page_name)
    if path is None:
        # Try journal display-name → filename fallback.
        journal_stem = _journal_display_to_filename(page_name)
        if journal_stem is not None:
            candidate = Path(graph_path).resolve() / "journals" / f"{journal_stem}.md"
            if candidate.is_file():
                path = candidate
    if path is None:
        return 0.0
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _collect_descendant_uuids(block: dict) -> set[str]:
    """Return UUIDs of every descendant of ``block`` (excluding the block itself)."""
    out: set[str] = set()
    for child in block.get("children", []):
        if not isinstance(child, dict):
            continue
        uuid = child.get("uuid")
        if uuid:
            out.add(str(uuid))
        out |= _collect_descendant_uuids(child)
    return out


def _source_page_name(page_info: dict) -> str:
    return page_info.get("originalName") or page_info.get("name") or "Unknown"


def _content_references_any(content: str, ref_strings: list[str]) -> bool:
    """Return True if ``content`` contains any of the reference strings.

    Bracket refs (``[[Tag]]``, ``#[[Tag]]``) use plain substring matching.
    Bare hash refs (``#Tag``) are checked against content padded with a
    trailing space so that end-of-string tags are caught without false-
    positive prefix matches (``#meeting`` does not match ``#meetings``).
    """
    padded = content + " "
    for s in ref_strings:
        if s.startswith("#") and "[[" not in s:
            # Bare #Tag: require space immediately after to avoid prefix matches.
            if (s + " ") in padded:
                return True
        else:
            if s in content:
                return True
    return False


def _find_matching_blocks(blocks: list[dict], ref_strings: list[str]) -> list[dict]:
    """Walk a block tree, returning every block whose content matches any ref.

    The returned blocks preserve their original ``children`` subtrees so they
    can be rendered directly.
    """
    out: list[dict] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        content = block.get("content", "") or ""
        if _content_references_any(content, ref_strings):
            out.append(block)
        children = block.get("children") or []
        if children:
            out.extend(_find_matching_blocks(children, ref_strings))
    return out


async def get_linked_references(
    client: LogseqClient,
    config: LogseqConfig,
    tag: str,
    since_days: int | None = None,
    limit: int | None = None,
    include_namespace_children: bool = False,
) -> List[TextContent]:
    """Return blocks across the graph that reference a page, with their full subtrees.

    Programmatic equivalent of Logseq's "Linked References" right-side panel.
    Each matching block is rendered with its complete subtree of children,
    grouped under the source page that contains it. Groups are sorted by source
    page modification time (most recent first) when ``LOGSEQ_GRAPH_PATH`` is set.

    Args:
        tag: Page name as it appears in Logseq (e.g. ``"Kz/Inn Hub"``).
        since_days: Only include matches from source pages modified in the last
            N days (filesystem mtime), anchored at local midnight. ``0`` means
            "today only". Requires ``LOGSEQ_GRAPH_PATH``. ``None`` (default)
            disables the filter.
        limit: Cap total matches returned. When set, the fetch loop stops as
            soon as the cap is reached — large graphs return quickly but the
            returned total reflects "at least this many", not the exact graph
            total. ``None`` (default) returns all (and is exact).
        include_namespace_children: When ``True``, also include refs to
            namespace descendants (e.g. ``"Kz/Inn Hub/Sub"``). Mirrors what
            Logseq's panel shows. Default ``False`` = exact tag only.
    """
    try:
        _log.debug(
            "%s called: tag=%r since_days=%s limit=%s namespace=%s",
            __name__,
            tag,
            since_days,
            limit,
            include_namespace_children,
        )

        if not tag or not tag.strip():
            return [TextContent(type="text", text="❌ tag must be a non-empty string.")]

        if since_days is not None and since_days < 0:
            return [
                TextContent(type="text", text="❌ since_days must be non-negative.")
            ]

        if limit is not None and limit < 0:
            return [TextContent(type="text", text="❌ limit must be non-negative.")]

        if since_days is not None and not config.graph_path:
            return [
                TextContent(
                    type="text",
                    text=(
                        "❌ since_days requires LOGSEQ_GRAPH_PATH "
                        "(filesystem mtime is the source of truth for modification time)."
                    ),
                )
            ]

        # Build filter-description notes once so both the "Found 0" early
        # return and the success header carry the same context (the user can
        # always tell whether a filter caused an empty result).
        filter_notes: list[str] = []
        if since_days is not None:
            if since_days == 0:
                filter_notes.append("today only")
            else:
                filter_notes.append(
                    f"last {since_days} day" + ("" if since_days == 1 else "s")
                )
        if include_namespace_children:
            filter_notes.append("including namespace children")

        def _with_notes(base: str, extra: list[str] | None = None) -> str:
            all_notes = filter_notes + (extra or [])
            return base + (" (" + ", ".join(all_notes) + ")" if all_notes else "")

        # Degenerate request: caller explicitly asked for zero results.
        if limit == 0:
            return [
                TextContent(
                    type="text",
                    text=_with_notes(
                        f"Found 0 references to [[{tag}]]", ["limit=0 requested"]
                    ),
                )
            ]

        # Tags to enumerate references for (the primary + optional ns descendants).
        source_tags: list[str] = [tag]
        if include_namespace_children:
            ns_pages = await client.get_pages_from_namespace(tag)
            for p in ns_pages or []:
                if not isinstance(p, dict):
                    continue
                name = p.get("originalName") or p.get("name")
                if name and name != tag:
                    source_tags.append(name)

        # The strings we look for inside block content. Three forms per tag:
        #   [[Tag]]     — standard wiki-link (always)
        #   #[[Tag]]    — hashtag with brackets (always; delimited by ]])
        #   #Tag        — bare hashtag (only for tags without spaces; the
        #                 space-padding trick in _content_references_any
        #                 prevents #meeting from matching #meetings)
        ref_strings: list[str] = []
        for t in source_tags:
            ref_strings.append(f"[[{t}]]")
            ref_strings.append(f"#[[{t}]]")
            if " " not in t:
                ref_strings.append(f"#{t}")

        # Collect the set of linking pages (union across source tags).
        # The API returns groups where group[0] is the linking page. The block
        # entries that may follow in group[1:] are unreliable in the wild — we
        # ignore them and re-derive matches from each page's full tree below.
        linking_page_names: list[str] = []
        seen: set[str] = set()
        for st in source_tags:
            groups = await client.get_page_linked_references(st)
            for group in groups or []:
                if not isinstance(group, list) or not group:
                    continue
                page_info = group[0]
                if not isinstance(page_info, dict):
                    continue
                name = _source_page_name(page_info)
                if name and name not in seen:
                    seen.add(name)
                    linking_page_names.append(name)

        # Privacy: drop linking pages tagged with any exclude_tag.
        excluded = await client.excluded_page_names()
        if excluded:
            linking_page_names = [
                n for n in linking_page_names if n.lower() not in excluded
            ]

        # Resolve mtimes (for since_days filter and recency sort).
        page_mtimes: dict[str, float] = {}
        if config.graph_path:
            for name in linking_page_names:
                page_mtimes[name] = _resolve_page_mtime(config.graph_path, name)

        if since_days is not None:
            # Anchor at local midnight so `since_days=N` means "last N calendar
            # days" rather than a rolling N×86400-second window. `since_days=0`
            # therefore means "modified today".
            today_midnight = datetime.datetime.combine(
                datetime.date.today(), datetime.time.min
            ).timestamp()
            cutoff = today_midnight - (since_days * _SECONDS_PER_DAY)
            linking_page_names = [
                n for n in linking_page_names if page_mtimes.get(n, 0.0) >= cutoff
            ]

        # Sort linking pages by mtime descending so the most recent ones come
        # first; combined with the early break below, `limit` actually skips
        # the expensive tree fetches for older pages.
        linking_page_names.sort(key=lambda n: -page_mtimes.get(n, 0.0))

        # For each linking page, fetch its full tree and find matching blocks.
        # When `limit` is set, stop as soon as we have enough matches — for a
        # tag with hundreds of linking pages this avoids fetching every tree.
        rendered: list[tuple[str, list[dict]]] = []
        total_matches = 0
        limit_reached = False
        for name in linking_page_names:
            tree = await client.get_page_blocks_tree(name)
            if not tree:
                continue
            matches = _find_matching_blocks(tree, ref_strings)
            if not matches:
                continue
            # Dedup: drop any matched block whose UUID is a descendant of
            # another matched block (its subtree already contains it).
            descendant_uuids: set[str] = set()
            for m in matches:
                descendant_uuids |= _collect_descendant_uuids(m)
            matches = [
                m for m in matches if str(m.get("uuid", "")) not in descendant_uuids
            ]
            if matches:
                rendered.append((name, matches))
                total_matches += len(matches)
                if limit is not None and total_matches >= limit:
                    limit_reached = True
                    break

        if not rendered:
            return [
                TextContent(
                    type="text",
                    text=_with_notes(f"Found 0 references to [[{tag}]]"),
                )
            ]

        # Apply limit cap (the last page may have pushed us slightly over).
        if limit is not None:
            capped: list[tuple[str, list[dict]]] = []
            remaining = limit
            for page_name, matches in rendered:
                if remaining <= 0:
                    break
                take = matches[:remaining]
                capped.append((page_name, take))
                remaining -= len(take)
            rendered = capped

        total_returned = sum(len(m) for _, m in rendered)

        if limit_reached:
            plural = "" if total_returned == 1 else "s"
            base = f"Showing {total_returned} reference{plural} to [[{tag}]]"
            header = _with_notes(base, ["limit reached, more may exist"])
        else:
            plural = "" if total_matches == 1 else "s"
            header = _with_notes(
                f"Found {total_matches} reference{plural} to [[{tag}]]"
            )

        lines: list[str] = [header, ""]
        for page_name, matches in rendered:
            lines.append(f"## {page_name}")
            for subtree in matches:
                lines.extend(format_block_tree(subtree, level=0))
            lines.append("")

        return [TextContent(type="text", text="\n".join(lines).rstrip() + "\n")]

    except Exception as exc:
        _log.error("exception in %s: %s", __name__, exc, exc_info=True)
        return [
            TextContent(type="text", text=f"❌ Error fetching linked references: {exc}")
        ]
