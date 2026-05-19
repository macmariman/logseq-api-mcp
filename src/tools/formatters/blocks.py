"""Pure formatters for Logseq block data."""

import re

_UUID_REF_PATTERN = re.compile(
    r"\[\[([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\]\]"
)


def resolve_uuid_refs(content: str, uuid_map: dict[str, str]) -> str:
    """Replace [[uuid]] patterns with [[Page Name]] using a pre-resolved map.

    Args:
        content: Block content string potentially containing UUID refs.
        uuid_map: Dict mapping uuid string → page name.

    Returns:
        Content string with UUIDs replaced by page names where known.

    Complexity: O(C) where C is content length.
    """

    def _replace(match: re.Match) -> str:
        uuid = match.group(1)
        name = uuid_map.get(uuid)
        return f"[[{name}]]" if name else match.group(0)

    return _UUID_REF_PATTERN.sub(_replace, content)


def collect_block_uuids(blocks: list[dict]) -> set[str]:
    """Recursively collect all page-reference UUIDs from block content strings.

    Args:
        blocks: List of block dicts with 'content' and 'children' keys.

    Returns:
        Set of UUID strings found in content.

    Complexity: O(N * C) where N is block count, C is average content length.
    """
    uuids: set[str] = set()
    for block in blocks:
        content = block.get("content", "")
        uuids.update(_UUID_REF_PATTERN.findall(content))
        children = block.get("children", [])
        if children:
            uuids.update(collect_block_uuids(children))
    return uuids


def format_block_tree(
    block: dict,
    level: int = 0,
    max_level: int = -1,
    db_properties: dict[str, dict] | None = None,
    uuid_map: dict[str, str] | None = None,
) -> list[str]:
    """Recursively format a Logseq block tree into display lines.

    Args:
        block: Raw Logseq block dict with content, children, properties.
        level: Current recursion depth (0 = root).
        max_level: Maximum depth to recurse; -1 means unlimited.
        db_properties: Optional DB-mode properties keyed by block UUID.
        uuid_map: Optional UUID-to-name resolution map for DB mode refs.

    Returns:
        List of formatted display lines.

    Complexity: O(N) where N is total block count in the subtree.
    """
    content = block.get("content", "").strip()
    if not content:
        return []

    if uuid_map:
        content = resolve_uuid_refs(content, uuid_map)

    indent = "  " * level
    if content.startswith(("- ", "* ", "+ ")) or content in ("-", "*", "+"):
        line = f"{indent}{content}"
    else:
        line = f"{indent}- {content}"

    lines = [line]

    if db_properties:
        uuid = str(block.get("uuid", ""))
        extra_props = db_properties.get(uuid, {})
        for key, value in extra_props.items():
            if f"{key}::" not in content:
                lines.append(f"{indent}  {key}:: {value}")

    children = block.get("children", [])
    if not children:
        return lines
    if max_level != -1 and level >= max_level:
        return lines

    for child in children:
        lines.extend(
            format_block_tree(child, level + 1, max_level, db_properties, uuid_map)
        )
    return lines


def format_block_detail(block: dict, is_child: bool = False) -> list[str]:
    """Format a single block with full metadata for get_block_content output.

    Args:
        block: Raw Logseq block dict.
        is_child: Whether this block is rendered as a child (affects indentation).

    Returns:
        List of formatted display lines.

    Complexity: O(P) where P is the property count.
    """
    indent = "  " if is_child else ""
    lines: list[str] = []

    content = block.get("content", "").strip()
    uuid = block.get("uuid", "N/A")
    level = block.get("level", 0)

    lines.append(f"{indent}📝 **Block** (UUID: {uuid}, Level: {level})")
    if content:
        lines.append(f"{indent}   Content: {content}")

    props = block.get("properties", {})
    if props:
        lines.append(f"{indent}   Properties:")
        for k, v in props.items():
            lines.append(f"{indent}     {k}:: {v}")

    page = block.get("page", {})
    if page:
        page_name = page.get("name") or page.get("originalName", "")
        if page_name:
            lines.append(f"{indent}   Page: {page_name}")

    children = block.get("children", [])
    if children:
        lines.append(f"{indent}   Children ({len(children)}):")
        for child in children:
            lines.extend(format_block_detail(child, is_child=True))

    return lines


def format_search_snippet(content: str, max_len: int = 150) -> str:
    """Truncate block content to a search-result snippet.

    Args:
        content: Raw block content string.
        max_len: Maximum character length before truncation.

    Returns:
        Possibly-truncated content string.

    Complexity: O(1).
    """
    content = content.strip()
    if len(content) > max_len:
        return content[:max_len] + "..."
    return content
