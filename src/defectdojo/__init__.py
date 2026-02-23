import os
from mcp.server.fastmcp import FastMCP

# Import registration functions
from defectdojo import findings_tools, products_tools, engagements_tools, tests_tools, users_tools

# Initialize FastMCP server
mcp = FastMCP("defectdojo")

# Register tools by calling functions from modules
findings_tools.register_tools(mcp)
products_tools.register_tools(mcp)
engagements_tools.register_tools(mcp)
tests_tools.register_tools(mcp)
users_tools.register_tools(mcp)


def main():
    """Initialize and run the MCP server."""
    print("Starting DefectDojo MCP server...")
    mcp.run(transport='stdio')

if __name__ == "__main__":
    # Initialize and run the server
    main()
