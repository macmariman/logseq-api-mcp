"""Tool registry: bind discovered tool functions to a FastMCP server."""

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

    @param mcp_server FastMCP instance.
    @param client     Shared LogseqClient (one aiohttp session for the process lifetime).
    @param config     Shared immutable LogseqConfig.
    @returns None.
    @throws Nothing.
    @complexity O(T) where T is the discovered-tool count.
    """
    for tool_name in tools.__all__:
        tool_function = getattr(tools, tool_name)
        bound = partial(tool_function, client, config)
        bound.__name__ = tool_function.__name__  # type: ignore[attr-defined]
        bound.__doc__ = tool_function.__doc__
        mcp_server.tool()(bound)
