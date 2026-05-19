"""Tests for get_pages_tree_from_namespace tool."""

from src.client.config import LogseqConfig
from tests.conftest import FakeLogseqClient
from src.tools.get_pages_tree_from_namespace import _run

_cfg = LogseqConfig("http://x", "t")

_FLAT_TREE = [
    {
        "originalName": "Project/Alpha",
        "name": "project/alpha",
        "uuid": "p1",
        "journal?": False,
        "createdAt": 0,
        "updatedAt": 0,
        "children": [],
    },
    {
        "originalName": "Project/Beta",
        "name": "project/beta",
        "uuid": "p2",
        "journal?": False,
        "createdAt": 0,
        "updatedAt": 0,
        "children": [],
    },
]

_NESTED_TREE = [
    {
        "originalName": "Project",
        "name": "project",
        "uuid": "p0",
        "journal?": False,
        "createdAt": 0,
        "updatedAt": 0,
        "children": [
            {
                "originalName": "Project/Alpha",
                "name": "project/alpha",
                "uuid": "p1",
                "journal?": False,
                "createdAt": 0,
                "updatedAt": 0,
                "children": [],
            },
        ],
    },
]


class TestGetPagesTreeFromNamespace:
    async def test_tree_single_level(self):
        client = FakeLogseqClient({"get_pages_tree_from_namespace": _FLAT_TREE})
        result = await _run(client, _cfg, "Project")
        assert "Project/Alpha" in result[0].text
        assert "Project/Beta" in result[0].text

    async def test_tree_nested(self):
        client = FakeLogseqClient({"get_pages_tree_from_namespace": _NESTED_TREE})
        result = await _run(client, _cfg, "Project")
        assert "Project" in result[0].text
        assert "Project/Alpha" in result[0].text

    async def test_tree_empty_namespace(self):
        client = FakeLogseqClient({"get_pages_tree_from_namespace": []})
        result = await _run(client, _cfg, "Empty")
        assert "Empty" in result[0].text
        assert "no pages" in result[0].text.lower() or "0" in result[0].text

    async def test_format_namespace_tree_uses_box_chars(self):
        client = FakeLogseqClient({"get_pages_tree_from_namespace": _NESTED_TREE})
        result = await _run(client, _cfg, "Project")
        assert "├──" in result[0].text or "└──" in result[0].text

    async def test_exception_returns_error(self):
        class ErrorClient(FakeLogseqClient):
            async def get_pages_tree_from_namespace(self, namespace):
                raise RuntimeError("tree error")

        result = await _run(ErrorClient(), _cfg, "Broken")
        assert "❌ Error fetching namespace tree" in result[0].text
