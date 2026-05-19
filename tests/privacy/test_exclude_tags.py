"""Tests for tag-based page exclusion."""

from src.privacy.exclude_tags import extract_tags, filter_pages, is_page_excluded


def test_extract_tags_from_list():
    assert extract_tags({"tags": ["private", "secret"]}) == ["private", "secret"]


def test_extract_tags_from_string():
    assert extract_tags({"tags": "private, secret"}) == ["private", "secret"]


def test_extract_tags_empty_dict():
    assert extract_tags({}) == []


def test_extract_tags_empty_list():
    assert extract_tags({"tags": []}) == []


def test_extract_tags_strips_whitespace():
    assert extract_tags({"tags": " private , secret "}) == ["private", "secret"]


def test_is_page_excluded_true_list():
    page = {"properties": {"tags": ["private"]}}
    assert is_page_excluded(page, ("private",)) is True


def test_is_page_excluded_true_string():
    page = {"properties": {"tags": "private,secret"}}
    assert is_page_excluded(page, ("private",)) is True


def test_is_page_excluded_false():
    page = {"properties": {"tags": ["public"]}}
    assert is_page_excluded(page, ("private",)) is False


def test_is_page_excluded_no_properties():
    assert is_page_excluded({}, ("private",)) is False


def test_is_page_excluded_empty_exclude_tags():
    page = {"properties": {"tags": ["private"]}}
    assert is_page_excluded(page, ()) is False


def test_filter_pages_removes_excluded():
    pages = [
        {"id": 1, "properties": {"tags": ["private"]}},
        {"id": 2, "properties": {"tags": ["public"]}},
    ]
    result = filter_pages(pages, ("private",))
    assert len(result) == 1
    assert result[0]["id"] == 2


def test_filter_pages_empty_exclude_returns_all():
    pages = [{"id": 1, "properties": {"tags": ["private"]}}]
    result = filter_pages(pages, ())
    assert len(result) == 1


def test_filter_pages_does_not_mutate_input():
    pages = [{"id": 1, "properties": {"tags": ["private"]}}]
    original_len = len(pages)
    filter_pages(pages, ("private",))
    assert len(pages) == original_len


def test_filter_pages_all_excluded_returns_empty():
    pages = [
        {"id": 1, "properties": {"tags": ["private"]}},
        {"id": 2, "properties": {"tags": ["secret"]}},
    ]
    result = filter_pages(pages, ("private", "secret"))
    assert result == []


def test_extract_tags_lowercases_input():
    assert extract_tags({"tags": ["Private", "SECRET"]}) == ["private", "secret"]


def test_extract_tags_handles_db_mode_dict_shape():
    assert extract_tags({"tags": [{"name": "private"}, {"name": "public"}]}) == [
        "private",
        "public",
    ]


def test_is_page_excluded_is_case_insensitive():
    page = {"properties": {"tags": ["Private"]}}
    assert is_page_excluded(page, ("private",)) is True
    assert is_page_excluded(page, ("PRIVATE",)) is True
