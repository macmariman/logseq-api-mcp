"""Public tool wrappers must accept client + config as first args (v1.0.1)."""

import inspect

import pytest

from src import tools

_WRAPPERS_TO_AUDIT = [
    "get_all_pages",
    "get_all_page_content",
    "get_page_blocks",
    "get_block_content",
    "get_page_backlinks",
    "get_linked_flashcards",
    "search",
    "query",
    "find_pages_by_property",
    "get_pages_from_namespace",
    "get_pages_tree_from_namespace",
]


@pytest.mark.parametrize("name", _WRAPPERS_TO_AUDIT)
def test_wrapper_first_two_params_are_client_and_config(name):
    fn = getattr(tools, name)
    sig = inspect.signature(fn)
    params = list(sig.parameters.values())
    assert params[0].name == "client"
    assert params[1].name == "config"
