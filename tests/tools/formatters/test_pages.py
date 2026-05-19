"""Tests for page formatters."""

from src.tools.formatters.pages import (
    format_namespace_tree,
    format_page_entry,
    format_pages_listing,
    format_timestamp,
)


def test_format_timestamp_none_returns_na():
    assert format_timestamp(None) == "N/A"


def test_format_timestamp_zero_returns_na():
    assert format_timestamp(0) == "N/A"


def test_format_timestamp_known_ms():
    # 2022-01-01 00:00:00 UTC = 1640995200000 ms
    result = format_timestamp(1640995200000)
    assert "2022-01-01" in result


def test_format_page_entry_journal():
    page = {
        "id": 1,
        "uuid": "abc",
        "originalName": "2024-01-01",
        "journal?": True,
        "createdAt": 0,
        "updatedAt": 0,
    }
    result = format_page_entry(page)
    assert "📅" in result
    assert "2024-01-01" in result


def test_format_page_entry_regular():
    page = {
        "id": 1,
        "uuid": "abc",
        "originalName": "My Page",
        "journal?": False,
        "createdAt": 0,
        "updatedAt": 0,
    }
    result = format_page_entry(page)
    assert "📄" in result
    assert "My Page" in result


def test_format_page_entry_includes_uuid():
    page = {
        "id": 42,
        "uuid": "test-uuid-123",
        "originalName": "Page X",
        "journal?": False,
        "createdAt": 0,
        "updatedAt": 0,
    }
    result = format_page_entry(page)
    assert "test-uuid-123" in result


def test_format_pages_listing_empty():
    result = format_pages_listing([])
    assert "No pages found" in result


def test_format_pages_listing_splits_journals():
    pages = [
        {
            "id": 1,
            "uuid": "a",
            "originalName": "Page A",
            "journal?": False,
            "createdAt": 0,
            "updatedAt": 0,
        },
        {
            "id": 2,
            "uuid": "b",
            "originalName": "2024-01-01",
            "journal?": True,
            "createdAt": 0,
            "updatedAt": 0,
        },
    ]
    result = format_pages_listing(pages)
    assert "REGULAR PAGES" in result
    assert "JOURNAL PAGES" in result
    assert "Page A" in result
    assert "2024-01-01" in result


def test_format_pages_listing_header():
    pages = [
        {
            "id": 1,
            "uuid": "a",
            "originalName": "P",
            "journal?": False,
            "createdAt": 0,
            "updatedAt": 0,
        }
    ]
    result = format_pages_listing(pages)
    assert "LOGSEQ PAGES LISTING" in result


def test_format_pages_listing_respects_slice():
    pages = [
        {
            "id": i,
            "uuid": str(i),
            "originalName": f"P{i}",
            "journal?": False,
            "createdAt": 0,
            "updatedAt": 0,
        }
        for i in range(10)
    ]
    result = format_pages_listing(pages, start=0, end=3)
    assert "showing indices 0-3" in result


def test_format_namespace_tree_single_level():
    pages = [
        {"originalName": "Projects/A"},
        {"originalName": "Projects/B"},
    ]
    lines = format_namespace_tree(pages)
    assert lines == ["Projects/A", "Projects/B"]


def test_format_namespace_tree_nested():
    pages = [
        {
            "originalName": "Projects",
            "children": [
                {"originalName": "Projects/Alpha", "children": []},
                {"originalName": "Projects/Beta", "children": []},
            ],
        }
    ]
    lines = format_namespace_tree(pages)
    assert "Projects" in lines[0]
    assert "├── Projects/Alpha" in lines[1]
    assert "└── Projects/Beta" in lines[2]


def test_format_namespace_tree_last_node_uses_corner():
    pages = [{"originalName": "Only", "children": []}]
    lines = format_namespace_tree(pages)
    assert "Only" in lines[0]
