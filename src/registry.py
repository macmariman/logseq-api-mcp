from mcp.server.fastmcp import FastMCP

from . import tools
from .vector import VECTOR_AVAILABLE
from .vector.config import load_vector_config


def register_all_tools(mcp_server: FastMCP) -> None:
    """Register all tools with the MCP server.

    Dynamically discovers and registers all functions from the tools module.
    When the vector extra is installed and LOGSEQ_VECTOR_ENABLED is set,
    also registers vector_search and vector_db_status.

    Args:
        mcp_server: The FastMCP server instance to register tools with.
    """
    for tool_name in tools.__all__:
        tool_function = getattr(tools, tool_name)
        mcp_server.tool()(tool_function)

    if VECTOR_AVAILABLE and load_vector_config() is not None:
        from .vector.search import vector_search
        from .vector.status import vector_db_status

        mcp_server.tool()(vector_search)
        mcp_server.tool()(vector_db_status)
