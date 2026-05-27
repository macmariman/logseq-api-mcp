"""MCP server bootstrap and registry wiring (v1.0.1)."""

from unittest.mock import MagicMock

from src.client.config import LogseqConfig
from src.client.logseq_client import LogseqClient
from src.registry import register_all_tools


def test_register_all_tools_accepts_mcp_client_and_config():
    mcp = MagicMock()
    cfg = LogseqConfig(endpoint="http://x/api", token="t")
    client = LogseqClient(cfg)
    register_all_tools(mcp, client, config=cfg)
    # mcp.tool() is called once per VISIBLE tool. Tools decorated with
    # @hidden remain in tools.__all__ (for tests/imports) but are not
    # announced to MCP clients — see src/tools/_marker.py.
    from src import tools

    # Mirror the registry's two filters: static @hidden marker, and the
    # dynamic fs_* gate (no graph_path or db_mode → fs_* tools are skipped).
    def _registered(name: str) -> bool:
        fn = getattr(tools, name)
        if getattr(fn, "_mcp_hidden", False):
            return False
        if name.startswith("fs_") and (cfg.db_mode or not cfg.graph_path):
            return False
        return True

    visible = [name for name in tools.__all__ if _registered(name)]
    assert mcp.tool.call_count == len(visible)


def test_server_module_imports_without_writing_stdout(capsys):
    # Import the server module — must not emit anything to stdout.
    import importlib
    import src.server

    importlib.reload(src.server)
    captured = capsys.readouterr()
    assert captured.out == "", f"server import polluted stdout: {captured.out!r}"
