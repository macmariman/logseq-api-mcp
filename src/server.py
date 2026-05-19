from mcp.server.fastmcp import FastMCP

from .logging_setup import setup_logging
from .registry import register_all_tools

setup_logging()

# Create an MCP server
mcp = FastMCP("Logseq API")

# Register all tools
register_all_tools(mcp)

if __name__ == "__main__":
    mcp.run()
