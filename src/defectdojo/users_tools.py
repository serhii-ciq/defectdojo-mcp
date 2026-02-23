from typing import Any, Dict, Optional
from defectdojo.client import get_client

# --- User & Group Tool Definitions ---


async def list_users(
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_superuser: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """List DefectDojo users with optional filtering and pagination.

    Users represent people who interact with DefectDojo — security
    engineers, developers, managers, etc.

    Args:
        username: Optional username filter (exact match).
        first_name: Optional first name filter (partial match).
        last_name: Optional last name filter (partial match).
        is_active: Filter by active status. ``True`` for active users only.
        is_superuser: Filter by superuser flag.
        limit: Maximum number of users to return per page (default: 50).
        offset: Number of records to skip (default: 0).

    Returns:
        Dictionary with status, data/error, and pagination metadata.
    """
    filters: Dict[str, Any] = {"limit": limit, "o": "id"}

    if username:
        filters["username"] = username
    if first_name:
        filters["first_name"] = first_name
    if last_name:
        filters["last_name"] = last_name
    if is_active is not None:
        filters["is_active"] = is_active
    if is_superuser is not None:
        filters["is_superuser"] = is_superuser
    if offset:
        filters["offset"] = offset

    client = get_client()
    result = await client.get_users(filters)

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


async def get_user(user_id: int) -> Dict[str, Any]:
    """Get a specific user by their ID.

    Returns the full user profile including username, email, first/last
    name, active status, and superuser flag.

    Args:
        user_id: The unique identifier of the user.

    Returns:
        Dictionary with status and user data or error.
    """
    client = get_client()
    result = await client.get_user(user_id)

    if "error" in result:
        return {
            "status": "error",
            "error": result["error"],
            "details": result.get("details", ""),
        }

    return {"status": "success", "data": result}


async def list_dojo_groups(
    name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """List DefectDojo groups with optional filtering and pagination.

    Groups are used for role-based access control (RBAC). They
    organize users into teams with shared permissions on products.

    Args:
        name: Optional group name filter (partial match).
        limit: Maximum number of groups to return per page (default: 50).
        offset: Number of records to skip (default: 0).

    Returns:
        Dictionary with status, data/error, and pagination metadata.
    """
    filters: Dict[str, Any] = {"limit": limit, "o": "id"}

    if name:
        filters["name"] = name
    if offset:
        filters["offset"] = offset

    client = get_client()
    result = await client.get_dojo_groups(filters)

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


async def list_dojo_group_members(
    group_id: Optional[int] = None,
    user_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """List members of DefectDojo groups with optional filtering.

    Returns group membership records linking users to groups with
    their assigned roles.

    Args:
        group_id: Optional group ID to filter members by.
        user_id: Optional user ID to find their group memberships.
        limit: Maximum number of records to return per page (default: 50).
        offset: Number of records to skip (default: 0).

    Returns:
        Dictionary with status, data/error, and pagination metadata.
    """
    filters: Dict[str, Any] = {"limit": limit, "o": "id"}

    if group_id is not None:
        filters["group"] = group_id
    if user_id is not None:
        filters["user"] = user_id
    if offset:
        filters["offset"] = offset

    client = get_client()
    result = await client.get_dojo_group_members(filters)

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


# --- Registration Function ---


def register_tools(mcp):
    """Register user-related tools with the MCP server instance."""
    mcp.tool(
        name="list_users",
        description="List DefectDojo users with optional filtering by username, name, and active status",
    )(list_users)
    mcp.tool(
        name="get_user",
        description="Get a specific DefectDojo user by their ID",
    )(get_user)
    mcp.tool(
        name="list_dojo_groups",
        description="List DefectDojo groups (teams) with optional name filtering",
    )(list_dojo_groups)
    mcp.tool(
        name="list_dojo_group_members",
        description="List members of DefectDojo groups with optional group/user filtering",
    )(list_dojo_group_members)
