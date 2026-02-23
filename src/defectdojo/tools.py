from mcp.server.fastmcp import FastMCP

# Import tool functions from the new modules
from .findings_tools import (
    get_findings,
    search_findings,
    count_findings,
    update_finding_status,
    add_finding_note,
    create_finding,
)
from .products_tools import list_products, count_products
from .engagements_tools import (
    list_engagements,
    get_engagement,
    create_engagement,
    update_engagement,
    close_engagement,
)

# Placeholder for the MCP instance - will be set by the main script
mcp = None

# --- Registration Function ---
# This function will be called by the main script to register tools with the MCP instance

def register_tools(mcp_instance: FastMCP):
    """Registers all tools with the provided FastMCP instance."""
    global mcp
    mcp = mcp_instance

    # Register Finding Tools
    mcp.tool(
        name="get_findings",
        description="Get findings with filtering options and pagination support"
    )(get_findings)

    mcp.tool(
        name="search_findings",
        description="Search for findings using a text query with pagination support"
    )(search_findings)

    mcp.tool(
        name="update_finding_status",
        description="Update the status of a finding (Active, Verified, False Positive, Mitigated, Inactive)"
    )(update_finding_status)

    mcp.tool(
        name="add_finding_note",
        description="Add a note to a finding"
    )(add_finding_note)

    mcp.tool(
        name="count_findings",
        description="Return total number of findings matching the given filters (lightweight, no full payload)"
    )(count_findings)

    mcp.tool(
        name="create_finding",
        description="Create a new finding"
    )(create_finding)

    # Register Product Tools
    mcp.tool(
        name="list_products",
        description="List all products with optional filtering and pagination support"
    )(list_products)

    mcp.tool(
        name="count_products",
        description="Return total number of products matching the given filters (lightweight, no full payload)"
    )(count_products)

    # Register Engagement Tools
    mcp.tool(
        name="list_engagements",
        description="List engagements with optional filtering and pagination support"
    )(list_engagements)

    mcp.tool(
        name="get_engagement",
        description="Get a specific engagement by ID"
    )(get_engagement)

    mcp.tool(
        name="create_engagement",
        description="Create a new engagement in DefectDojo"
        # Schema inferred from type hints and docstring
    )(create_engagement)

    mcp.tool(
        name="update_engagement",
        description="Update an existing engagement"
    )(update_engagement)

    mcp.tool(
        name="close_engagement",
        description="Close an engagement"
    )(close_engagement)
