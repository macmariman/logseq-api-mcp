"""Tests for conditional vector tool registration."""

from unittest.mock import MagicMock, patch

from src.registry import register_all_tools
from src.vector.config import VectorConfig
from pathlib import Path


def _make_mcp():
    mcp = MagicMock()
    mcp.tool.return_value = lambda fn: fn
    return mcp


def test_vector_tools_not_registered_when_deps_missing():
    mcp = _make_mcp()
    registered_names = []

    def capture_tool():
        def decorator(fn):
            registered_names.append(fn.__name__)
            return fn
        return decorator

    mcp.tool = capture_tool

    with patch("src.registry.VECTOR_AVAILABLE", False):
        register_all_tools(mcp)

    assert "vector_search" not in registered_names
    assert "vector_db_status" not in registered_names


def test_vector_tools_not_registered_when_config_is_none():
    mcp = _make_mcp()
    registered_names = []

    def capture_tool():
        def decorator(fn):
            registered_names.append(fn.__name__)
            return fn
        return decorator

    mcp.tool = capture_tool

    with patch("src.registry.VECTOR_AVAILABLE", True), \
         patch("src.registry.load_vector_config", return_value=None):
        register_all_tools(mcp)

    assert "vector_search" not in registered_names
    assert "vector_db_status" not in registered_names


def test_vector_tools_registered_when_available_and_configured():
    mcp = _make_mcp()
    registered_names = []

    def capture_tool():
        def decorator(fn):
            registered_names.append(fn.__name__)
            return fn
        return decorator

    mcp.tool = capture_tool

    cfg = VectorConfig(db_path=Path("/tmp/db"), graph_path=Path("/tmp/graph"))
    with patch("src.registry.VECTOR_AVAILABLE", True), \
         patch("src.registry.load_vector_config", return_value=cfg):
        register_all_tools(mcp)

    assert "vector_search" in registered_names
    assert "vector_db_status" in registered_names
