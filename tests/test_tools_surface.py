"""Tool surface contract.

Pinned to detect accidental additions/removals. Update both the list and
the expected count when adding or removing a tool from src/tools/.
"""

from src import tools


_EXPECTED = sorted(
    [
        "append_block_in_page",
        "create_page",
        "delete_block",
        "delete_page",
        "edit_block",
        "find_pages_by_property",
        "fs_read_page",
        "fs_write_page",
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


def test_tools_surface_is_pinned():
    assert sorted(tools.__all__) == _EXPECTED
    assert len(tools.__all__) == len(_EXPECTED)
