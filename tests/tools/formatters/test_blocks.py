"""Tests for block formatters."""

from src.tools.formatters.blocks import (
    collect_block_uuids,
    format_block_detail,
    format_block_tree,
    format_search_snippet,
    resolve_uuid_refs,
)


def test_format_block_tree_simple():
    block = {"content": "Hello World", "children": [], "uuid": "u1"}
    lines = format_block_tree(block)
    assert len(lines) == 1
    assert "Hello World" in lines[0]


def test_format_block_tree_indents_children():
    block = {
        "content": "Parent",
        "uuid": "u1",
        "children": [
            {"content": "Child", "uuid": "u2", "children": []}
        ],
    }
    lines = format_block_tree(block)
    assert len(lines) == 2
    assert "Parent" in lines[0]
    assert "Child" in lines[1]
    assert lines[1].startswith("  ")  # indented


def test_format_block_tree_empty_content_returns_empty():
    block = {"content": "", "children": [], "uuid": "u1"}
    assert format_block_tree(block) == []


def test_format_block_tree_respects_max_level():
    block = {
        "content": "Root",
        "uuid": "u1",
        "children": [
            {
                "content": "Level 1",
                "uuid": "u2",
                "children": [
                    {"content": "Level 2", "uuid": "u3", "children": []}
                ],
            }
        ],
    }
    lines = format_block_tree(block, max_level=1)
    texts = " ".join(lines)
    assert "Root" in texts
    assert "Level 1" in texts
    assert "Level 2" not in texts


def test_format_block_tree_resolves_uuid_refs():
    block = {
        "content": "See [[12345678-1234-1234-1234-123456789abc]]",
        "uuid": "u1",
        "children": [],
    }
    uuid_map = {"12345678-1234-1234-1234-123456789abc": "My Page"}
    lines = format_block_tree(block, uuid_map=uuid_map)
    assert "[[My Page]]" in lines[0]


def test_collect_block_uuids_finds_uuids():
    blocks = [
        {"content": "See [[12345678-1234-1234-1234-123456789abc]]", "children": []}
    ]
    uuids = collect_block_uuids(blocks)
    assert "12345678-1234-1234-1234-123456789abc" in uuids


def test_collect_block_uuids_recursive():
    blocks = [
        {
            "content": "Parent",
            "children": [
                {
                    "content": "[[aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee]]",
                    "children": [],
                }
            ],
        }
    ]
    uuids = collect_block_uuids(blocks)
    assert "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" in uuids


def test_resolve_uuid_refs_replaces_known():
    uuid_map = {"aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee": "Test Page"}
    result = resolve_uuid_refs("See [[aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee]]", uuid_map)
    assert "[[Test Page]]" in result


def test_resolve_uuid_refs_keeps_unknown():
    result = resolve_uuid_refs("See [[aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee]]", {})
    assert "[[aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee]]" in result


def test_format_search_snippet_short():
    assert format_search_snippet("short") == "short"


def test_format_search_snippet_truncates():
    long = "x" * 200
    result = format_search_snippet(long, max_len=150)
    assert result.endswith("...")
    assert len(result) == 153


def test_format_block_detail_includes_uuid():
    block = {
        "uuid": "test-uuid",
        "content": "Block content",
        "level": 1,
        "children": [],
    }
    lines = format_block_detail(block)
    text = "\n".join(lines)
    assert "test-uuid" in text
    assert "Block content" in text


def test_format_block_detail_includes_properties():
    block = {
        "uuid": "u1",
        "content": "test",
        "level": 0,
        "properties": {"status": "active"},
        "children": [],
    }
    lines = format_block_detail(block)
    text = "\n".join(lines)
    assert "status" in text
    assert "active" in text
