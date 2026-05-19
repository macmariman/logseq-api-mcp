"""Tests for get_page_blocks tool."""

from tests.conftest import FakeLogseqClient
from src.tools.get_page_blocks import _run


class TestGetPageBlocks:
    async def test_returns_tree_structure(self, sample_block_data):
        client = FakeLogseqClient({"get_page_blocks_tree": [sample_block_data]})
        result = await _run(client, "My Page")
        assert len(result) == 1
        assert "PAGE BLOCKS TREE STRUCTURE" in result[0].text
        assert "Test block content" in result[0].text

    async def test_empty_page(self):
        client = FakeLogseqClient({"get_page_blocks_tree": []})
        result = await _run(client, "Empty Page")
        assert "has no blocks" in result[0].text

    async def test_block_count_shown(self, sample_block_data):
        blocks = [sample_block_data, {**sample_block_data, "id": 2, "uuid": "b"}]
        client = FakeLogseqClient({"get_page_blocks_tree": blocks})
        result = await _run(client, "My Page")
        assert "Total blocks: 2" in result[0].text

    async def test_nested_children_shown(self):
        blocks = [
            {
                "id": 1,
                "uuid": "p",
                "content": "Parent block",
                "level": 1,
                "page": {"id": 1, "name": "P"},
                "properties": {},
                "children": [
                    {
                        "id": 2,
                        "uuid": "c",
                        "content": "Child block",
                        "level": 2,
                        "children": [],
                    }
                ],
            }
        ]
        client = FakeLogseqClient({"get_page_blocks_tree": blocks})
        result = await _run(client, "My Page")
        assert "Parent block" in result[0].text
        assert "Child block" in result[0].text

    async def test_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_page_blocks_tree(self, page_identifier):
                raise RuntimeError("API down")

        result = await _run(ErrorClient(), "My Page")
        assert "❌ Error fetching page blocks: API down" in result[0].text
