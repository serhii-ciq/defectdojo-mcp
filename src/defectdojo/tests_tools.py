from typing import Any, Dict, Optional
from defectdojo.client import get_client

# --- Test Tool Definitions ---


async def list_tests(
    engagement_id: Optional[int] = None,
    test_type: Optional[int] = None,
    tags: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """List tests with optional filtering and pagination.

    Tests represent individual scan runs or manual testing sessions within
    an engagement. Each test contains findings produced by a specific tool.

    Args:
        engagement_id: Optional engagement ID to filter tests by.
        test_type: Optional test type ID to filter by.
        tags: Optional tag to filter by.
        limit: Maximum number of tests to return per page (default: 20).
        offset: Number of records to skip (default: 0).

    Returns:
        Dictionary with status, data/error, and pagination metadata.
    """
    filters: Dict[str, Any] = {"limit": limit, "o": "-id"}

    if engagement_id is not None:
        filters["engagement"] = engagement_id
    if test_type is not None:
        filters["test_type"] = test_type
    if tags:
        filters["tags"] = tags
    if offset:
        filters["offset"] = offset

    client = get_client()
    result = await client.get_tests(filters)

    if "error" in result:
        return {
            "status": "error",
            "error": result["error"],
            "details": result.get("details", ""),
        }

    applied = {k: v for k, v in filters.items() if k not in ("limit", "offset", "o")}
    response: Dict[str, Any] = {"status": "success", "data": result}
    if applied:
        response["applied_filters"] = applied
    return response


async def get_test(test_id: int) -> Dict[str, Any]:
    """Get a specific test by its ID.

    Args:
        test_id: The unique identifier of the test.

    Returns:
        Dictionary with status and test data or error.
    """
    client = get_client()
    result = await client.get_test(test_id)

    if "error" in result:
        return {
            "status": "error",
            "error": result["error"],
            "details": result.get("details", ""),
        }

    return {"status": "success", "data": result}


# --- Registration Function ---


def register_tools(mcp):
    """Register test-related tools with the MCP server instance."""
    mcp.tool(
        name="list_tests",
        description="List tests (scan runs) with optional filtering by engagement, test type, and tags",
    )(list_tests)
    mcp.tool(
        name="get_test",
        description="Get a specific test by its ID",
    )(get_test)
