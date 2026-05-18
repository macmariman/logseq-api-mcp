"""Pure formatters for Logseq search results."""

from .blocks import format_search_snippet


def format_search_results_markdown_mode(
    result: dict,
    query: str,
    limit: int = 20,
    include_blocks: bool = True,
    include_pages: bool = True,
    include_files: bool = False,
    excluded_page_names: frozenset[str] = frozenset(),
) -> str:
    """Format logseq.App.search results for markdown-mode Logseq.

    Args:
        result: Raw API response dict with 'blocks', 'pages', 'pages-content', 'files'.
        query: Original search query string (for header).
        limit: Maximum number of results to display per section.
        include_blocks: Whether to include block-content results.
        include_pages: Whether to include page-name results.
        include_files: Whether to include file-name results.
        excluded_page_names: Lowercased page names to suppress.

    Returns:
        Multi-line formatted markdown string.

    Complexity: O(N) where N is total result count.
    """
    parts: list[str] = [f"# Search Results for '{query}'\n"]

    if include_blocks and result.get("blocks"):
        blocks = result["blocks"]
        parts.append(f"## Content Blocks ({len(blocks)} found)")
        for i, block in enumerate(blocks[:limit]):
            content = block.get("block/content", "").strip()
            if content:
                parts.append(f"{i + 1}. {format_search_snippet(content)}")
        parts.append("")

    if include_pages and result.get("pages-content"):
        snippets = [
            s for s in result["pages-content"]
            if (s.get("block/snippet", "") or "").lower() not in excluded_page_names
        ]
        if snippets:
            parts.append(f"## Page Snippets ({len(snippets)} found)")
            for i, snippet in enumerate(snippets[:limit]):
                text = snippet.get("block/snippet", "").strip()
                text = text.replace("$pfts_2lqh>$", "").replace("$<pfts_2lqh$", "")
                if text:
                    parts.append(f"{i + 1}. {format_search_snippet(text, max_len=200)}")
            parts.append("")

    if include_pages and result.get("pages"):
        visible = [p for p in result["pages"] if p.lower() not in excluded_page_names]
        if visible:
            parts.append(f"## Matching Pages ({len(visible)} found)")
            for page in visible:
                parts.append(f"- {page}")
            parts.append("")

    if include_files and result.get("files"):
        files = result["files"]
        parts.append(f"## Matching Files ({len(files)} found)")
        for f in files:
            parts.append(f"- {f}")
        parts.append("")

    if result.get("has-more?"):
        parts.append("*More results available — increase limit to see more*")

    total = (
        len(result.get("blocks", []))
        + len(result.get("pages", []))
        + len(result.get("pages-content", []))
        + len(result.get("files", []))
    )
    parts.append(f"\n**Total results: {total}**")
    return "\n".join(parts)


def format_search_results_db_mode(
    result: dict,
    query: str,
    limit: int = 20,
    include_blocks: bool = True,
    include_pages: bool = True,
    include_files: bool = False,
    excluded_page_names: frozenset[str] = frozenset(),
) -> str:
    """Format logseq.App.search results for DB-mode Logseq.

    Args:
        result: Raw API response dict with 'blocks' (mixed pages + blocks).
        query: Original search query string (for header).
        limit: Maximum number of results to display per section.
        include_blocks: Whether to include block-content results.
        include_pages: Whether to include page-name results.
        include_files: Whether to include file-name results.
        excluded_page_names: Lowercased page names to suppress.

    Returns:
        Multi-line formatted markdown string.

    Complexity: O(N) where N is total result count.
    """
    parts: list[str] = [f"# Search Results for '{query}'\n"]
    blocks_raw = result.get("blocks", [])

    page_results = [b for b in blocks_raw if b.get("page?")]
    block_results = [b for b in blocks_raw if not b.get("page?")]

    if include_pages and page_results:
        visible = [
            p for p in page_results
            if (p.get("fullTitle") or p.get("title") or p.get("content", "")).lower()
            not in excluded_page_names
        ]
        if visible:
            parts.append(f"## Matching Pages ({len(visible)} found)")
            for page in visible:
                name = page.get("fullTitle") or page.get("title") or page.get("content", "")
                parts.append(f"- {name}")
            parts.append("")

    if include_blocks and block_results:
        parts.append(f"## Content Blocks ({len(block_results)} found)")
        for i, block in enumerate(block_results[:limit]):
            content = block.get("content", "").strip()
            content = content.replace("$pfts_2lqh>$", "").replace("$<pfts_2lqh$", "")
            if content:
                uuid = block.get("uuid", "")
                page_id = block.get("page", "")
                parts.append(f"{i + 1}. {format_search_snippet(content)}")
                parts.append(f"   uuid: {uuid}  page: {page_id}")
        parts.append("")

    if include_files and result.get("files"):
        files = result["files"]
        parts.append(f"## Matching Files ({len(files)} found)")
        for f in files:
            parts.append(f"- {f}")
        parts.append("")

    if result.get("hasMore?"):
        parts.append("*More results available — increase limit to see more*")

    total = len(blocks_raw) + len(result.get("files", []))
    parts.append(f"\n**Total results: {total}**")
    return "\n".join(parts)
