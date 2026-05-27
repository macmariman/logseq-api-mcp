"""Tool registry: bind discovered tool functions to a FastMCP server."""

import inspect
from functools import partial

from mcp.server.fastmcp import FastMCP

from . import tools
from .client.config import LogseqConfig
from .client.logseq_client import LogseqClient


def register_all_tools(
    mcp_server: FastMCP,
    client: LogseqClient,
    config: LogseqConfig,
) -> None:
    """Register every discovered tool with the FastMCP server.

    Adaptive binding: if a tool's first two parameters are named ``client``
    and ``config``, a :func:`functools.partial` injects the shared client and
    config so MCP callers see only the remaining schema. Tools that still use
    the legacy wrapper signature (without leading ``client, config``) are
    registered directly; they continue to construct their own client via
    ``load_config()`` until tasks C2-C5 migrate them.

    @param mcp_server FastMCP instance.
    @param client     Shared LogseqClient (one aiohttp session for the process lifetime).
    @param config     Shared immutable LogseqConfig.
    @returns None.
    @throws Nothing.
    @complexity O(T) where T is the discovered-tool count.
    """
    for tool_name in tools.__all__:
        tool_function = getattr(tools, tool_name)
        # Skip tools marked with @hidden — see src/tools/_marker.py. They
        # stay in tools.__all__ for tests and direct imports but are not
        # announced to MCP clients.
        if getattr(tool_function, "_mcp_hidden", False):
            continue
        # Dynamic gate for filesystem tools: fs_* only registers when the
        # graph is file-mode and LOGSEQ_GRAPH_PATH points at it. We skip
        # silently here; missing config is reported by the tool itself if
        # somehow called.
        if tool_name.startswith("fs_") and (config.db_mode or not config.graph_path):
            continue
        sig = inspect.signature(tool_function)
        first_two = list(sig.parameters)[:2]
        if first_two == ["client", "config"]:
            bound = partial(tool_function, client, config)
            bound.__name__ = tool_function.__name__  # type: ignore[attr-defined]
            bound.__doc__ = tool_function.__doc__
            mcp_server.tool()(bound)
        else:
            mcp_server.tool()(tool_function)
