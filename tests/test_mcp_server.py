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
    # mcp.tool() called once per discovered tool
    from src import tools

    assert mcp.tool.call_count == len(tools.__all__)


def test_server_module_imports_without_writing_stdout(capsys):
    # Import the server module — must not emit anything to stdout.
    import importlib
    import src.server

    importlib.reload(src.server)
    captured = capsys.readouterr()
    assert captured.out == "", f"server import polluted stdout: {captured.out!r}"
