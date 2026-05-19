"""v1.0.1 tool surface contract."""

from src import tools


_EXPECTED = sorted(
    [
        "append_block_in_page",
        "create_page",
        "delete_block",
        "delete_page",
        "edit_block",
        "find_pages_by_property",
        "get_all_page_content",
        "get_all_pages",
        "get_block_content",
        "get_linked_flashcards",
        "get_page_backlinks",
        "get_page_blocks",
        "get_pages_from_namespace",
        "get_pages_tree_from_namespace",
        "insert_nested_block",
        "query",
        "rename_page",
        "search",
        "set_block_properties",
        "update_block",
        "update_page",
    ]
)


def test_tools_surface_is_exactly_21():
    assert sorted(tools.__all__) == _EXPECTED
    assert len(tools.__all__) == 21
