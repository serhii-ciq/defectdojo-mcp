from typing import Any, Dict, List, Optional
from defectdojo.client import get_client

# --- Finding Tool Definitions ---


def _build_findings_filters(
    *,
    product_name: Optional[str] = None,
    severity: Optional[str] = None,
    active: Optional[bool] = None,
    is_mitigated: Optional[bool] = None,
    duplicate: Optional[bool] = None,
    engagement_id: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """Build a query-parameter dict accepted by the DefectDojo findings API.

    DefectDojo v2 ``/api/v2/findings/`` does **not** support a ``status``
    query parameter.  Filtering by state is done through boolean fields:

    * ``active`` – ``True`` for open findings, ``False`` for closed.
    * ``is_mitigated`` – ``True`` for mitigated findings.
    * ``duplicate`` – ``True`` / ``False``.

    Args:
        product_name: Optional product name filter.
        severity: Optional severity filter (Critical, High, Medium, Low, Info).
        active: Filter by active state.  ``True`` = open findings,
            ``False`` = inactive/closed findings.
        is_mitigated: Filter by mitigation state.
        duplicate: Filter by duplicate flag.
        engagement_id: Optional engagement ID to scope findings to a specific
            engagement (maps to ``test__engagement`` API parameter).
        limit: Maximum number of findings to return per page.
        offset: Number of records to skip.

    Returns:
        Dictionary of query parameters.
    """
    filters: Dict[str, Any] = {
        "limit": limit,
        "o": "id",  # deterministic ordering
    }

    if product_name:
        filters["product_name"] = product_name
    if severity:
        filters["severity"] = severity
    if active is not None:
        filters["active"] = active
    if is_mitigated is not None:
        filters["is_mitigated"] = is_mitigated
    if duplicate is not None:
        filters["duplicate"] = duplicate
    if engagement_id is not None:
        filters["test__engagement"] = engagement_id
    if offset:
        filters["offset"] = offset

    return filters


async def get_findings(
    product_name: Optional[str] = None,
    severity: Optional[str] = None,
    active: Optional[bool] = None,
    is_mitigated: Optional[bool] = None,
    duplicate: Optional[bool] = None,
    engagement_id: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """Get findings with optional filters and pagination.

    Args:
        product_name: Optional product name filter.
        severity: Optional severity filter (Critical, High, Medium, Low, Info).
        active: Filter by active state.  ``True`` = open findings,
            ``False`` = inactive/closed findings.
        is_mitigated: Filter by mitigation state.
        duplicate: Filter by duplicate flag. ``False`` to exclude duplicates,
            ``True`` to return only duplicates.
        engagement_id: Optional engagement ID to scope findings to a specific engagement.
        limit: Maximum number of findings to return per page (default: 20).
        offset: Number of records to skip (default: 0).

    Returns:
        Dictionary with status, data/error, and pagination metadata.
    """
    filters = _build_findings_filters(
        product_name=product_name,
        severity=severity,
        active=active,
        is_mitigated=is_mitigated,
        duplicate=duplicate,
        engagement_id=engagement_id,
        limit=limit,
        offset=offset,
    )

    client = get_client()
    result = await client.get_findings(filters)

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


async def search_findings(
    query: str,
    product_name: Optional[str] = None,
    severity: Optional[str] = None,
    active: Optional[bool] = None,
    is_mitigated: Optional[bool] = None,
    duplicate: Optional[bool] = None,
    engagement_id: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """Search for findings using a text query with pagination.

    Args:
        query: Text to search for in findings.
        product_name: Optional product name filter.
        severity: Optional severity filter (Critical, High, Medium, Low, Info).
        active: Filter by active state.  ``True`` = open findings,
            ``False`` = inactive/closed findings.
        is_mitigated: Filter by mitigation state.
        duplicate: Filter by duplicate flag. ``False`` to exclude duplicates,
            ``True`` to return only duplicates.
        engagement_id: Optional engagement ID to scope findings to a specific engagement.
        limit: Maximum number of findings to return per page (default: 20).
        offset: Number of records to skip (default: 0).

    Returns:
        Dictionary with status, data/error, and pagination metadata.
    """
    filters = _build_findings_filters(
        product_name=product_name,
        severity=severity,
        active=active,
        is_mitigated=is_mitigated,
        duplicate=duplicate,
        engagement_id=engagement_id,
        limit=limit,
        offset=offset,
    )

    client = get_client()
    result = await client.search_findings(query, filters)

    if "error" in result:
        return {
            "status": "error",
            "error": result["error"],
            "details": result.get("details", ""),
        }

    applied = {k: v for k, v in filters.items() if k not in ("limit", "offset", "o")}
    applied["query"] = query
    response: Dict[str, Any] = {"status": "success", "data": result}
    if applied:
        response["applied_filters"] = applied
    return response


async def count_findings(
    product_name: Optional[str] = None,
    severity: Optional[str] = None,
    active: Optional[bool] = None,
    is_mitigated: Optional[bool] = None,
    duplicate: Optional[bool] = None,
    engagement_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Return the total number of findings matching the given filters.

    This is a lightweight alternative to ``get_findings`` when you only
    need the count.  It requests a single record (``limit=1``) and reads
    the ``count`` field from the paginated response.

    Args:
        product_name: Optional product name filter.
        severity: Optional severity filter (Critical, High, Medium, Low, Info).
        active: Filter by active state.  ``True`` = open findings,
            ``False`` = inactive/closed findings.
        is_mitigated: Filter by mitigation state.
        duplicate: Filter by duplicate flag. ``False`` to exclude duplicates,
            ``True`` to return only duplicates.
        engagement_id: Optional engagement ID to scope findings to a specific engagement.

    Returns:
        Dictionary with status and total count.
    """
    filters = _build_findings_filters(
        product_name=product_name,
        severity=severity,
        active=active,
        is_mitigated=is_mitigated,
        duplicate=duplicate,
        engagement_id=engagement_id,
        limit=1,  # minimize payload – we only need the count
        offset=0,
    )

    client = get_client()
    result = await client.get_findings(filters)

    if "error" in result:
        return {
            "status": "error",
            "error": result["error"],
            "details": result.get("details", ""),
        }

    applied = {k: v for k, v in filters.items() if k not in ("limit", "offset", "o")}
    response: Dict[str, Any] = {
        "status": "success",
        "count": result.get("count", 0),
    }
    if applied:
        response["applied_filters"] = applied
    return response


async def update_finding_status(finding_id: int, status: str) -> Dict[str, Any]:
    """Update the status of a finding.

    Args:
        finding_id: ID of the finding to update
        status: New status for the finding (Active, Verified, False Positive, Mitigated, Inactive)

    Returns:
        Dictionary with status and data/error
    """
    data = {"active": True}  # Default to active

    # Map common status values to API fields
    status_lower = status.lower()
    if status_lower == "false positive":
        data["false_p"] = True
    elif status_lower == "verified":
        data["verified"] = True
    elif status_lower == "mitigated":
        data["active"] = False
        data["mitigated"] = True
    elif status_lower == "inactive":
        data["active"] = False
    elif status_lower != "active":
        return {"status": "error", "error": f"Unsupported status: {status}. Use Active, Verified, False Positive, Mitigated, or Inactive."}

    # Clear conflicting flags if setting a specific status
    if data.get("false_p"):
        data.pop("verified", None)
        data.pop("active", None)
        data.pop("mitigated", None)
    elif data.get("verified"):
         data.pop("false_p", None)
         data["active"] = True
         data.pop("mitigated", None)
    elif data.get("mitigated"):
         data.pop("false_p", None)
         data.pop("verified", None)
         data["active"] = False
    elif not data.get("active", True):
         data.pop("false_p", None)
         data.pop("verified", None)
         data.pop("mitigated", None)
         data["active"] = False
    else:
         data.pop("false_p", None)
         data.pop("verified", None)
         data.pop("mitigated", None)
         data["active"] = True

    client = get_client()
    result = await client.update_finding(finding_id, data)

    if "error" in result:
        return {"status": "error", "error": result["error"], "details": result.get("details", "")}

    return {"status": "success", "data": result}


async def add_finding_note(finding_id: int, note: str) -> Dict[str, Any]:
    """Add a note to a finding.

    Args:
        finding_id: ID of the finding to add a note to
        note: Text content of the note

    Returns:
        Dictionary with status and data/error
    """
    if not note.strip():
        return {"status": "error", "error": "Note content cannot be empty"}

    client = get_client()
    result = await client.add_note_to_finding(finding_id, note)

    if "error" in result:
        return {"status": "error", "error": result["error"], "details": result.get("details", "")}

    return {"status": "success", "data": result}


async def create_finding(title: str, test_id: int, severity: str, description: str,
                        cwe: Optional[int] = None, cvssv3: Optional[str] = None,
                        mitigation: Optional[str] = None, impact: Optional[str] = None,
                        steps_to_reproduce: Optional[str] = None) -> Dict[str, Any]:
    """Create a new finding.

    Args:
        title: Title of the finding
        test_id: ID of the test to associate the finding with
        severity: Severity level (Critical, High, Medium, Low, Info)
        description: Description of the finding
        cwe: Optional CWE identifier
        cvssv3: Optional CVSS v3 score string
        mitigation: Optional mitigation steps
        impact: Optional impact description
        steps_to_reproduce: Optional steps to reproduce

    Returns:
        Dictionary with status and data/error
    """
    valid_severities = ["critical", "high", "medium", "low", "info"]
    normalized_severity = severity.lower()
    if normalized_severity not in valid_severities:
        valid_display = [s.title() for s in valid_severities]
        return {"status": "error", "error": f"Invalid severity '{severity}'. Must be one of: {', '.join(valid_display)}"}

    api_severity = severity.title()

    data = {
        "title": title,
        "test": test_id,
        "severity": api_severity,
        "description": description,
        "active": True,
        "verified": False,
    }

    if cwe is not None:
        data["cwe"] = cwe
    if cvssv3:
        data["cvssv3"] = cvssv3
    if mitigation:
        data["mitigation"] = mitigation
    if impact:
        data["impact"] = impact
    if steps_to_reproduce:
        data["steps_to_reproduce"] = steps_to_reproduce

    client = get_client()
    result = await client.create_finding(data)

    if "error" in result:
        return {"status": "error", "error": result["error"], "details": result.get("details", "")}

    return {"status": "success", "data": result}


async def get_finding(finding_id: int) -> Dict[str, Any]:
    """Get a specific finding by its ID.

    Returns the full finding object including notes, tags, endpoints,
    and all metadata fields.

    Args:
        finding_id: The unique identifier of the finding.

    Returns:
        Dictionary with status and finding data or error.
    """
    client = get_client()
    result = await client.get_finding(finding_id)

    if "error" in result:
        return {
            "status": "error",
            "error": result["error"],
            "details": result.get("details", ""),
        }

    return {"status": "success", "data": result}


# --- Registration Function ---

def register_tools(mcp):
    """Register finding-related tools with the MCP server instance."""
    mcp.tool(name="get_findings", description="Get findings with filtering options and pagination support")(get_findings)
    mcp.tool(name="search_findings", description="Search for findings using a text query with pagination support")(search_findings)
    mcp.tool(name="count_findings", description="Return total number of findings matching the given filters (lightweight, no full payload)")(count_findings)
    mcp.tool(name="get_finding", description="Get a specific finding by its ID with full details")(get_finding)
    mcp.tool(name="update_finding_status", description="Update the status of a finding (Active, Verified, False Positive, Mitigated, Inactive)")(update_finding_status)
    mcp.tool(name="add_finding_note", description="Add a note to a finding")(add_finding_note)
    mcp.tool(name="create_finding", description="Create a new finding")(create_finding)
