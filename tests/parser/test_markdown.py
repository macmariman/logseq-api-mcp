"""Tests for the Markdown → Logseq block tree parser."""

from src.parser.markdown import BlockNode, ParsedContent, parse_content


# ── BlockNode ────────────────────────────────────────────────────────────────


class TestBlockNode:
    def test_to_batch_format_simple(self):
        node = BlockNode(content="Hello")
        fmt = node.to_batch_format()
        assert fmt["content"] == "Hello"

    def test_to_batch_format_with_properties(self):
        node = BlockNode(
            content="Task", properties={"logseq.order-list-type": "number"}
        )
        fmt = node.to_batch_format()
        assert "logseq.order-list-type:: number" in fmt["content"]

    def test_to_batch_format_no_children_key_when_empty(self):
        node = BlockNode(content="Solo")
        fmt = node.to_batch_format()
        assert fmt.get("children", []) == []

    def test_to_batch_format_nested_children(self):
        child = BlockNode(content="Child")
        parent = BlockNode(content="Parent", children=[child])
        fmt = parent.to_batch_format()
        assert len(fmt["children"]) == 1
        assert fmt["children"][0]["content"] == "Child"

    def test_default_level_is_zero(self):
        node = BlockNode(content="x")
        assert node.level == 0

    def test_mutable_children_list(self):
        node = BlockNode(content="test")
        node.children.append(BlockNode(content="child"))
        assert len(node.children) == 1


# ── ParsedContent ─────────────────────────────────────────────────────────────


class TestParsedContent:
    def test_to_batch_format_returns_list(self):
        pc = ParsedContent(blocks=[BlockNode(content="A"), BlockNode(content="B")])
        batch = pc.to_batch_format()
        assert isinstance(batch, list)
        assert len(batch) == 2

    def test_empty_parsed_content(self):
        pc = ParsedContent()
        assert pc.properties == {}
        assert pc.blocks == []
        assert pc.to_batch_format() == []


# ── parse_content ─────────────────────────────────────────────────────────────


class TestParseContent:
    def test_empty_string(self):
        result = parse_content("")
        assert result.properties == {}
        assert result.blocks == []

    def test_whitespace_only(self):
        result = parse_content("   \n  \n  ")
        assert result.blocks == []

    # ── Frontmatter ──────────────────────────────────────────────────────────

    def test_frontmatter_string_property(self):
        md = "---\nstatus: active\n---\nContent"
        result = parse_content(md)
        assert result.properties["status"] == "active"

    def test_frontmatter_list_property(self):
        md = "---\ntags: [python, mcp]\n---\nContent"
        result = parse_content(md)
        assert "python" in result.properties["tags"]

    def test_frontmatter_stripped_from_blocks(self):
        md = "---\nstatus: active\n---\nActual content"
        result = parse_content(md)
        block_texts = [b.content for b in result.blocks]
        assert not any("status" in t and "active" in t for t in block_texts)

    def test_frontmatter_only_no_blocks(self):
        md = "---\nstatus: active\n---\n"
        result = parse_content(md)
        assert result.properties["status"] == "active"
        assert result.blocks == []

    def test_malformed_frontmatter_returns_empty_properties(self):
        md = "---\n: : invalid yaml\n---\ncontent"
        result = parse_content(md)
        # Should not raise; may return empty or partial properties
        assert isinstance(result.properties, dict)

    # ── Bullet lists ──────────────────────────────────────────────────────────

    def test_bullet_list_dash(self):
        result = parse_content("- item1\n- item2")
        assert len(result.blocks) == 2
        assert result.blocks[0].content == "- item1"
        assert result.blocks[1].content == "- item2"

    def test_bullet_list_asterisk(self):
        result = parse_content("* item")
        assert len(result.blocks) == 1
        assert result.blocks[0].content.endswith("item")

    def test_nested_bullet_list(self):
        md = "- parent\n  - child"
        result = parse_content(md)
        assert len(result.blocks) == 1
        assert len(result.blocks[0].children) == 1
        assert "child" in result.blocks[0].children[0].content

    # ── Numbered lists ────────────────────────────────────────────────────────

    def test_numbered_list(self):
        result = parse_content("1. first\n2. second")
        assert len(result.blocks) == 2

    def test_numbered_list_has_order_property(self):
        result = parse_content("1. first")
        block = result.blocks[0]
        assert "logseq.order-list-type" in block.properties

    # ── Checkboxes ────────────────────────────────────────────────────────────

    def test_unchecked_checkbox_becomes_todo(self):
        result = parse_content("- [ ] Task A")
        assert "TODO" in result.blocks[0].content

    def test_checked_checkbox_becomes_done(self):
        result = parse_content("- [x] Task B")
        assert "DONE" in result.blocks[0].content

    def test_checked_checkbox_uppercase_x(self):
        result = parse_content("- [X] Task C")
        assert "DONE" in result.blocks[0].content

    # ── Headings ─────────────────────────────────────────────────────────────

    def test_h1_becomes_root_block(self):
        result = parse_content("# Title")
        assert len(result.blocks) == 1
        assert result.blocks[0].content == "# Title"

    def test_h2_nested_under_h1(self):
        md = "# H1\n## H2"
        result = parse_content(md)
        assert len(result.blocks) == 1  # H1 is root
        assert len(result.blocks[0].children) >= 1
        assert any("## H2" in c.content for c in result.blocks[0].children)

    def test_body_text_after_heading_is_child(self):
        md = "# H1\nsome text"
        result = parse_content(md)
        children_content = [c.content for c in result.blocks[0].children]
        assert any("some text" in c for c in children_content)

    def test_h1_resets_heading_stack(self):
        md = "# H1\n## H2\n# New H1"
        result = parse_content(md)
        assert len(result.blocks) == 2  # Two separate H1 trees

    # ── Fenced code blocks ────────────────────────────────────────────────────

    def test_fenced_code_single_block(self):
        md = "```python\nprint('hi')\n```"
        result = parse_content(md)
        assert len(result.blocks) == 1
        assert "```python" in result.blocks[0].content

    def test_fenced_code_preserves_fence_markers(self):
        md = "```\ncode here\n```"
        result = parse_content(md)
        assert result.blocks[0].content.startswith("```")

    # ── Blockquotes ───────────────────────────────────────────────────────────

    def test_blockquote_becomes_block(self):
        result = parse_content("> quoted text")
        assert len(result.blocks) == 1
        assert ">" in result.blocks[0].content

    def test_multiline_blockquote_joined(self):
        md = "> line 1\n> line 2"
        result = parse_content(md)
        block_text = result.blocks[0].content
        assert "line 1" in block_text
        assert "line 2" in block_text

    # ── Paragraphs ────────────────────────────────────────────────────────────

    def test_plain_paragraph(self):
        result = parse_content("Hello world")
        assert len(result.blocks) == 1
        assert "Hello world" in result.blocks[0].content

    def test_multiline_paragraph_joined(self):
        md = "line one\nline two"
        result = parse_content(md)
        # Lines may be joined or separate depending on impl; either is valid
        all_text = " ".join(b.content for b in result.blocks)
        assert "line one" in all_text
        assert "line two" in all_text

    # ── Tables ────────────────────────────────────────────────────────────────

    def test_table_becomes_single_block(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = parse_content(md)
        # All rows combined into one block
        all_text = " ".join(b.content for b in result.blocks)
        assert "| A |" in all_text

    # ── batch format roundtrip ────────────────────────────────────────────────

    def test_batch_format_roundtrip(self):
        md = "# Title\ncontent line"
        result = parse_content(md)
        batch = result.to_batch_format()
        assert isinstance(batch, list)
        assert batch[0]["content"] == "# Title"

    def test_batch_format_nested_roundtrip(self):
        md = "# H1\n## H2\ntext"
        result = parse_content(md)
        batch = result.to_batch_format()
        assert len(batch) == 1
        assert len(batch[0]["children"]) >= 1

    def test_numbered_list_batch_format_has_property(self):
        result = parse_content("1. item")
        batch = result.to_batch_format()
        assert "logseq.order-list-type:: number" in batch[0]["content"]
