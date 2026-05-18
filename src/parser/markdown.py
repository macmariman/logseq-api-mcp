"""Pure Markdown → Logseq block tree parser."""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Iterator

logger = logging.getLogger(__name__)

# ── Regex patterns ────────────────────────────────────────────────────────────

_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)
_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")
_BULLET = re.compile(r"^(\s*)([-*+])\s+(.*)$")
_NUMBERED = re.compile(r"^(\s*)(\d+)\.\s+(.*)$")
_CHECKBOX_UNCHECKED = re.compile(r"^\[ \]\s*")
_CHECKBOX_CHECKED = re.compile(r"^\[[xX]\]\s*")
_BLOCKQUOTE = re.compile(r"^>\s?(.*)$")
_FENCE_START = re.compile(r"^(`{3,}|~{3,})(\w*)$")
_FENCE_END = re.compile(r"^(`{3,}|~{3,})$")
_TABLE_ROW = re.compile(r"^\|.+\|")
_SEPARATOR = re.compile(r"^\|[-| :]+\|$")


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class BlockNode:
    """A single Logseq block with optional nested children.

    Args:
        content: Block text content.
        children: List of child BlockNodes.
        properties: Block-level property dict (e.g. logseq.order-list-type).
        level: Heading level 0-6 (0 = body block).

    Complexity: O(1) construction.
    """

    content: str
    children: list[BlockNode] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)
    level: int = 0

    def to_batch_format(self) -> dict:
        """Convert to Logseq IBatchBlock format.

        Properties are appended to content as 'key:: value' lines.

        Returns:
            Dict with 'content' (str) and 'children' (list) keys.

        Complexity: O(N) where N is total descendant count.
        """
        text = self.content
        for key, value in self.properties.items():
            prop_line = f"{key}:: {value}"
            if prop_line not in text:
                text = text + "\n" + prop_line
        result: dict = {"content": text}
        if self.children:
            result["children"] = [c.to_batch_format() for c in self.children]
        else:
            result["children"] = []
        return result


@dataclass
class ParsedContent:
    """Result of parsing a markdown document.

    Args:
        properties: Page-level properties extracted from YAML frontmatter.
        blocks: Top-level BlockNode list.

    Complexity: O(1) construction.
    """

    properties: dict = field(default_factory=dict)
    blocks: list[BlockNode] = field(default_factory=list)

    def to_batch_format(self) -> list[dict]:
        """Convert all blocks to Logseq IBatchBlock format.

        Returns:
            List of IBatchBlock dicts, one per top-level block.

        Complexity: O(N) where N is total block count.
        """
        return [b.to_batch_format() for b in self.blocks]


# ── Frontmatter extraction ────────────────────────────────────────────────────

def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and return (properties, remaining_text).

    Args:
        text: Raw markdown string.

    Returns:
        Tuple of (properties dict, text with frontmatter removed).

    Complexity: O(F) where F is frontmatter length.
    """
    match = _FRONTMATTER.match(text)
    if not match:
        return {}, text

    try:
        import yaml  # type: ignore[import]
        props = yaml.safe_load(match.group(1)) or {}
        if not isinstance(props, dict):
            props = {}
    except Exception:
        try:
            # Minimal fallback: parse 'key: value' lines
            props = {}
            for line in match.group(1).splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    props[k.strip()] = v.strip()
        except Exception as exc:
            logger.debug("Frontmatter parse fallback failed: %s", exc)
            props = {}

    return props, text[match.end():]


# ── Indent helpers ────────────────────────────────────────────────────────────

def _indent_level(spaces: str, tab_width: int = 2) -> int:
    """Return nesting level from a leading-whitespace string.

    Args:
        spaces: Leading whitespace string.
        tab_width: Number of spaces per indent level.

    Returns:
        Integer nesting level (0-based).

    Complexity: O(1).
    """
    expanded = spaces.replace("\t", " " * tab_width)
    return len(expanded) // tab_width


# ── Main parser ───────────────────────────────────────────────────────────────

class _Parser:
    """Stateful line-by-line parser converting markdown to a BlockNode tree.

    Complexity per call to parse(): O(L) where L is line count.
    """

    def __init__(self) -> None:
        self._roots: list[BlockNode] = []
        self._heading_stack: list[BlockNode] = []

    # ── Public entry point ────────────────────────────────────────────────────

    def parse(self, lines: list[str]) -> list[BlockNode]:
        """Parse a list of lines into a root-level BlockNode list.

        Args:
            lines: List of markdown lines (no trailing newlines required).

        Returns:
            List of top-level BlockNodes.

        Complexity: O(L) where L is line count.
        """
        i = 0
        while i < len(lines):
            line = lines[i]

            # Fenced code block
            fence_match = _FENCE_START.match(line)
            if fence_match:
                node, i = self._parse_fence(lines, i, fence_match.group(1))
                self._add_block(node)
                continue

            # Blockquote run
            if _BLOCKQUOTE.match(line):
                node, i = self._parse_blockquote(lines, i)
                self._add_block(node)
                continue

            # Table run
            if _TABLE_ROW.match(line):
                node, i = self._parse_table(lines, i)
                self._add_block(node)
                continue

            # Heading
            heading_match = _HEADING.match(line)
            if heading_match:
                node = self._parse_heading(heading_match)
                i += 1
                continue

            # Numbered list item
            numbered_match = _NUMBERED.match(line)
            if numbered_match:
                node, i = self._parse_list_item(lines, i, numbered_match, numbered=True)
                self._add_block(node)
                continue

            # Bullet list item
            bullet_match = _BULLET.match(line)
            if bullet_match:
                node, i = self._parse_list_item(lines, i, bullet_match, numbered=False)
                self._add_block(node)
                continue

            # Empty line
            if not line.strip():
                i += 1
                continue

            # Paragraph
            node, i = self._parse_paragraph(lines, i)
            self._add_block(node)

        return self._roots

    # ── Block parsers ─────────────────────────────────────────────────────────

    def _parse_heading(self, match: re.Match) -> BlockNode:
        """Parse a heading line and wire it into the heading hierarchy.

        Args:
            match: Regex match with groups (hashes, title).

        Returns:
            The created heading BlockNode (already added to tree).

        Complexity: O(D) where D is heading stack depth.
        """
        hashes = match.group(1)
        title = match.group(2).strip()
        level = len(hashes)
        node = BlockNode(content=f"{hashes} {title}", level=level)

        # Pop headings at the same or deeper level
        while self._heading_stack and self._heading_stack[-1].level >= level:
            self._heading_stack.pop()

        if self._heading_stack:
            self._heading_stack[-1].children.append(node)
        else:
            self._roots.append(node)

        self._heading_stack.append(node)
        return node

    def _parse_fence(
        self, lines: list[str], start: int, fence_char: str
    ) -> tuple[BlockNode, int]:
        """Collect lines between fenced code markers into a single block.

        Args:
            lines: Full line list.
            start: Index of the opening fence line.
            fence_char: The fence character sequence (``` or ~~~).

        Returns:
            Tuple of (BlockNode, next_line_index).

        Complexity: O(K) where K is code block line count.
        """
        block_lines = [lines[start]]
        i = start + 1
        while i < len(lines):
            block_lines.append(lines[i])
            if _FENCE_END.match(lines[i]) and i > start:
                i += 1
                break
            i += 1
        return BlockNode(content="\n".join(block_lines)), i

    def _parse_blockquote(
        self, lines: list[str], start: int
    ) -> tuple[BlockNode, int]:
        """Collect contiguous blockquote lines into one block.

        Args:
            lines: Full line list.
            start: Index of the first blockquote line.

        Returns:
            Tuple of (BlockNode, next_line_index).

        Complexity: O(K) where K is blockquote line count.
        """
        collected: list[str] = []
        i = start
        while i < len(lines) and _BLOCKQUOTE.match(lines[i]):
            collected.append(lines[i])
            i += 1
        return BlockNode(content="\n".join(collected)), i

    def _parse_table(
        self, lines: list[str], start: int
    ) -> tuple[BlockNode, int]:
        """Collect contiguous table rows into one block.

        Args:
            lines: Full line list.
            start: Index of the first table row.

        Returns:
            Tuple of (BlockNode, next_line_index).

        Complexity: O(K) where K is table row count.
        """
        collected: list[str] = []
        i = start
        while i < len(lines) and (_TABLE_ROW.match(lines[i]) or _SEPARATOR.match(lines[i])):
            collected.append(lines[i])
            i += 1
        return BlockNode(content="\n".join(collected)), i

    def _parse_paragraph(
        self, lines: list[str], start: int
    ) -> tuple[BlockNode, int]:
        """Collect consecutive non-special lines into a single paragraph block.

        Args:
            lines: Full line list.
            start: Index of the first paragraph line.

        Returns:
            Tuple of (BlockNode, next_line_index).

        Complexity: O(K) where K is paragraph line count.
        """
        collected: list[str] = []
        i = start
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                break
            if (
                _HEADING.match(line)
                or _FENCE_START.match(line)
                or _BLOCKQUOTE.match(line)
                or _TABLE_ROW.match(line)
                or _BULLET.match(line)
                or _NUMBERED.match(line)
            ):
                break
            collected.append(line.strip())
            i += 1
        return BlockNode(content=" ".join(collected)), i

    def _parse_list_item(
        self,
        lines: list[str],
        start: int,
        match: re.Match,
        numbered: bool,
    ) -> tuple[BlockNode, int]:
        """Parse a list item and its nested children.

        Args:
            lines: Full line list.
            start: Index of the current list item line.
            match: Regex match for the list item pattern.
            numbered: True if this is a numbered (ordered) list.

        Returns:
            Tuple of (BlockNode, next_line_index).

        Complexity: O(K) where K is item + children line count.
        """
        indent_str = match.group(1)
        text = match.group(3)
        current_level = _indent_level(indent_str)

        # Transform checkbox
        content = self._transform_checkbox(text)
        if not content.startswith("- "):
            content = f"- {content}"

        props: dict[str, str] = {}
        if numbered:
            props["logseq.order-list-type"] = "number"

        node = BlockNode(content=content, properties=props)
        i = start + 1

        # Consume indented children
        while i < len(lines):
            child_line = lines[i]
            if not child_line.strip():
                break

            child_num = _NUMBERED.match(child_line)
            child_bul = _BULLET.match(child_line)
            child_match = child_num or child_bul
            if not child_match:
                break

            child_indent = _indent_level(child_match.group(1))
            if child_indent <= current_level:
                break

            child_node, i = self._parse_list_item(
                lines, i, child_match, numbered=bool(child_num)
            )
            node.children.append(child_node)

        return node, i

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _transform_checkbox(text: str) -> str:
        """Replace markdown checkbox syntax with Logseq TODO/DONE markers.

        Args:
            text: Raw list item text (without bullet prefix).

        Returns:
            Text with [ ] → TODO and [x]/[X] → DONE.

        Complexity: O(1).
        """
        if _CHECKBOX_CHECKED.match(text):
            return "DONE " + _CHECKBOX_CHECKED.sub("", text).strip()
        if _CHECKBOX_UNCHECKED.match(text):
            return "TODO " + _CHECKBOX_UNCHECKED.sub("", text).strip()
        return text

    def _add_block(self, node: BlockNode) -> None:
        """Append a block as a child of the current heading or as a root block.

        Args:
            node: BlockNode to add.

        Complexity: O(1).
        """
        if self._heading_stack:
            self._heading_stack[-1].children.append(node)
        else:
            self._roots.append(node)


# ── Public API ────────────────────────────────────────────────────────────────

def parse_content(markdown: str) -> ParsedContent:
    """Parse a markdown string into a ParsedContent tree.

    Handles: YAML frontmatter, headings (H1-H6), bullet lists (-, *, +),
    numbered lists, checkboxes (→ TODO/DONE), blockquotes (>),
    fenced code blocks (``` or ~~~), markdown tables, and paragraphs.

    Args:
        markdown: Raw markdown string.

    Returns:
        ParsedContent with extracted properties and block tree.

    Raises:
        Nothing — malformed input degrades gracefully.

    Complexity: O(L) where L is line count.
    """
    if not markdown or not markdown.strip():
        return ParsedContent()

    properties, remaining = _parse_frontmatter(markdown)
    if not remaining.strip():
        return ParsedContent(properties=properties)

    lines = remaining.splitlines()
    parser = _Parser()
    blocks = parser.parse(lines)
    return ParsedContent(properties=properties, blocks=blocks)
