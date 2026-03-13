import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional, List
from urllib.parse import parse_qs
from defectdojo.client import get_client

# --- Engagement Tool Definitions ---
VALID_ENGAGEMENT_STATUSES = [
    "Not Started",
    "Blocked",
    "Cancelled",
    "Completed",
    "In Progress",
    "On Hold",
    "Waiting for Resource",
]


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    """Parse ISO datetime values returned by DefectDojo into UTC."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_iso_date(value: Any) -> Optional[date]:
    """Parse ISO date values returned by DefectDojo."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _coerce_bool(value: Any) -> Optional[bool]:
    """Convert common bool-like values into bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    return None


def _coerce_int(value: Any) -> Optional[int]:
    """Convert integer-like values into int."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _parse_legacy_offset(value: Any) -> Optional[int]:
    """Parse offset from legacy page token values."""
    parsed_int = _coerce_int(value)
    if parsed_int is not None:
        return parsed_int
    if isinstance(value, str) and "offset=" in value:
        query = parse_qs(value.lstrip("?"))
        offsets = query.get("offset")
        if offsets:
            return _coerce_int(offsets[0])
    return None


def _load_legacy_filters(filters: Optional[Any]) -> Optional[Dict[str, Any]]:
    """Load legacy JSON filters payload into a dictionary."""
    if not filters:
        return {}
    if isinstance(filters, dict):
        return filters
    if not isinstance(filters, str):
        return None
    try:
        parsed = json.loads(filters)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _matches_derived_filters(
    engagement: Dict[str, Any],
    now_utc: datetime,
    stale_only: bool,
    active_recent_days: Optional[int],
    overdue_days: Optional[int],
) -> bool:
    """Apply local post-filters that are not directly exposed in tool params."""
    if stale_only:
        stale_recent_days = 14 if active_recent_days is None else active_recent_days
        stale_overdue_days = 7 if overdue_days is None else overdue_days

        if not engagement.get("active"):
            return False
        if engagement.get("status") != "In Progress":
            return False

        updated_at = _parse_iso_datetime(engagement.get("updated"))
        target_end = _parse_iso_date(engagement.get("target_end"))

        stale_by_update = (
            updated_at is not None
            and updated_at < (now_utc - timedelta(days=stale_recent_days))
        )
        stale_by_overdue = (
            target_end is not None
            and target_end <= (now_utc.date() - timedelta(days=stale_overdue_days))
        )
        return stale_by_update or stale_by_overdue

    if active_recent_days is not None:
        if not engagement.get("active"):
            return False
        updated_at = _parse_iso_datetime(engagement.get("updated"))
        if updated_at is None:
            return False
        if updated_at < (now_utc - timedelta(days=active_recent_days)):
            return False

    if overdue_days is not None:
        target_end = _parse_iso_date(engagement.get("target_end"))
        if target_end is None:
            return False
        if target_end > (now_utc.date() - timedelta(days=overdue_days)):
            return False

    return True


def _build_applied_filters(
    product_id: Optional[int],
    status: Optional[str],
    name: Optional[str],
    stale_only: bool,
    active_recent_days: Optional[int],
    overdue_days: Optional[int],
) -> Dict[str, Any]:
    """Build user-visible filter metadata for response payloads."""
    applied: Dict[str, Any] = {}
    if product_id is not None:
        applied["product"] = product_id
    if status is not None:
        applied["status"] = status
    if name is not None:
        applied["name"] = name

    if stale_only:
        applied["stale_only"] = True
        applied["stale_recent_days"] = 14 if active_recent_days is None else active_recent_days
        applied["stale_overdue_days"] = 7 if overdue_days is None else overdue_days
        return applied

    if active_recent_days is not None:
        applied["active_recent_days"] = active_recent_days
    if overdue_days is not None:
        applied["overdue_days"] = overdue_days
    return applied

async def list_engagements(product_id: Optional[int] = None,
                          status: Optional[str] = None,
                          name: Optional[str] = None,
                          limit: int = 20,
                          offset: int = 0,
                          stale_only: bool = False,
                          active_recent_days: Optional[int] = None,
                          overdue_days: Optional[int] = None,
                          filters: Optional[Any] = None,
                          page_size: Optional[str] = None,
                          page_token: Optional[str] = None) -> Dict[str, Any]:
    """List engagements with optional filtering and pagination.

    Args:
        product_id: Optional product ID filter
        status: Optional status filter (e.g., 'Not Started', 'In Progress', 'Completed')
        name: Optional name filter (partial match)
        limit: Maximum number of engagements to return per page (default: 20)
        offset: Number of records to skip (default: 0)
        stale_only: Return only stale engagements (active + In Progress + stale by age or due date).
            Uses stale defaults: updated older than 14 days OR overdue by more than 7 days.
        active_recent_days: Return only active engagements updated in the last N days.
            When stale_only=True, this becomes the stale recency threshold (defaults to 14).
        overdue_days: Return only engagements with target_end older than N days.
            When stale_only=True, this becomes the stale overdue threshold (defaults to 7).
        filters: Backward-compatible legacy filters (JSON object string or object).
        page_size: Backward-compatible alias for limit.
        page_token: Backward-compatible alias for offset or 'offset=...&limit=...'.

    Returns:
        Dictionary with status, data/error, and pagination metadata
    """
    legacy_filters = _load_legacy_filters(filters)
    if legacy_filters is None:
        return {"status": "error", "error": "filters must be a JSON object string"}

    legacy_product = legacy_filters.get("product_id", legacy_filters.get("product"))
    if product_id is None and legacy_product is not None:
        parsed_product = _coerce_int(legacy_product)
        if parsed_product is None:
            return {"status": "error", "error": "Invalid product_id in filters"}
        product_id = parsed_product

    if status is None and isinstance(legacy_filters.get("status"), str):
        status = legacy_filters["status"]
    if name is None and isinstance(legacy_filters.get("name"), str):
        name = legacy_filters["name"]

    if not stale_only and "stale_only" in legacy_filters:
        legacy_stale_only = _coerce_bool(legacy_filters.get("stale_only"))
        if legacy_stale_only is None:
            return {"status": "error", "error": "Invalid stale_only in filters"}
        stale_only = legacy_stale_only

    if active_recent_days is None and "active_recent_days" in legacy_filters:
        active_recent_days = _coerce_int(legacy_filters.get("active_recent_days"))
        if active_recent_days is None:
            return {"status": "error", "error": "Invalid active_recent_days in filters"}

    if overdue_days is None and "overdue_days" in legacy_filters:
        overdue_days = _coerce_int(legacy_filters.get("overdue_days"))
        if overdue_days is None:
            return {"status": "error", "error": "Invalid overdue_days in filters"}

    if limit == 20:
        limit_source = page_size if page_size is not None else legacy_filters.get("limit")
        if limit_source is not None:
            parsed_limit = _coerce_int(limit_source)
            if parsed_limit is None:
                return {"status": "error", "error": "Invalid limit/page_size value"}
            limit = parsed_limit

    if offset == 0:
        offset_source = page_token if page_token is not None else legacy_filters.get("offset")
        if offset_source is not None:
            parsed_offset = _parse_legacy_offset(offset_source)
            if parsed_offset is None:
                return {"status": "error", "error": "Invalid offset/page_token value"}
            offset = parsed_offset

    if limit < 1:
        return {"status": "error", "error": "limit must be >= 1"}
    if offset < 0:
        return {"status": "error", "error": "offset must be >= 0"}
    if active_recent_days is not None and active_recent_days < 0:
        return {"status": "error", "error": "active_recent_days must be >= 0"}
    if overdue_days is not None and overdue_days < 0:
        return {"status": "error", "error": "overdue_days must be >= 0"}

    base_filters: Dict[str, Any] = {"o": "-updated"}
    if product_id:
        base_filters["product"] = product_id
    if status:
        if status not in VALID_ENGAGEMENT_STATUSES:
            return {
                "status": "error",
                "error": (
                    f"Invalid status filter '{status}'. Must be one of: "
                    f"{', '.join(VALID_ENGAGEMENT_STATUSES)}"
                ),
            }
        base_filters["status"] = status
    if name:
        base_filters["name"] = name  # Or name__icontains if supported

    client = get_client()

    use_post_filter = stale_only or active_recent_days is not None or overdue_days is not None
    if not use_post_filter:
        filters = dict(base_filters)
        filters["limit"] = limit
        if offset:
            filters["offset"] = offset

        result = await client.get_engagements(filters)
        if "error" in result:
            return {"status": "error", "error": result["error"], "details": result.get("details", "")}
        return {"status": "success", "data": result}

    # Post-filter mode: scan all sorted pages and apply local derived filters.
    scan_limit = 100
    scan_offset = 0
    filtered_results: List[Dict[str, Any]] = []
    now_utc = datetime.now(timezone.utc)

    while True:
        scan_filters = dict(base_filters)
        scan_filters["limit"] = scan_limit
        scan_filters["offset"] = scan_offset

        result = await client.get_engagements(scan_filters)
        if "error" in result:
            return {"status": "error", "error": result["error"], "details": result.get("details", "")}

        page_results = result.get("results", [])
        if not page_results:
            break

        for engagement in page_results:
            if _matches_derived_filters(
                engagement,
                now_utc,
                stale_only,
                active_recent_days,
                overdue_days,
            ):
                filtered_results.append(engagement)

        if not result.get("next"):
            break
        scan_offset += scan_limit

    total_count = len(filtered_results)
    paged_results = filtered_results[offset:offset + limit]
    response_data = {
        "count": total_count,
        "next": None,
        "previous": None,
        "results": paged_results,
    }
    if offset + limit < total_count:
        response_data["next"] = f"offset={offset + limit}&limit={limit}"
    if offset > 0:
        prev_offset = max(offset - limit, 0)
        response_data["previous"] = f"offset={prev_offset}&limit={limit}"

    response: Dict[str, Any] = {"status": "success", "data": response_data}
    applied = _build_applied_filters(
        product_id=product_id,
        status=status,
        name=name,
        stale_only=stale_only,
        active_recent_days=active_recent_days,
        overdue_days=overdue_days,
    )
    if applied:
        response["applied_filters"] = applied
    return response


async def get_engagement(engagement_id: int) -> Dict[str, Any]:
    """Get a specific engagement by ID.

    Args:
        engagement_id: ID of the engagement to retrieve

    Returns:
        Dictionary with status and data/error
    """
    client = get_client()
    result = await client.get_engagement(engagement_id)

    if "error" in result:
        return {"status": "error", "error": result["error"], "details": result.get("details", "")}

    return {"status": "success", "data": result}


async def create_engagement(product_id: int, name: str, target_start: str, target_end: str, status: str, lead_id: int = None, description: str = None, version: str = None, build_id: str = None, commit_hash: str = None, branch_tag: str = None, engagement_type: str = None, deduplication_on_engagement: bool = None, tags: list = None):
    """
    Creates a new engagement in DefectDojo.

    Args:
        product_id: ID of the product.
        name: Name of the engagement.
        target_start: Start date (YYYY-MM-DD).
        target_end: End date (YYYY-MM-DD).
        status: Engagement status ('Not Started', 'Blocked', 'Cancelled', 'Completed', 'In Progress', 'On Hold', 'Waiting for Resource').
        lead_id: Optional ID of the engagement lead (user ID).
        description: Optional engagement description.
        version: Optional product version tested.
        build_id: Optional build ID.
        commit_hash: Optional commit hash.
        branch_tag: Optional branch or tag.
        engagement_type: Optional engagement type ('Interactive' or 'CI/CD').
        deduplication_on_engagement: Optional flag to enable deduplication within this engagement.
        tags: Optional list of tags.

    Returns:
        JSON response from the API.
    """
    # endpoint = "/api/v2/engagements/" # Endpoint handled by client method
    if status not in VALID_ENGAGEMENT_STATUSES:
        # Use raise ValueError for internal validation errors
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {', '.join(VALID_ENGAGEMENT_STATUSES)}"
        )

    # Validate engagement_type if provided
    if engagement_type and engagement_type not in ["Interactive", "CI/CD"]:
         raise ValueError(f"Invalid engagement_type '{engagement_type}'. Must be 'Interactive' or 'CI/CD'.")

    data = {
        "product": product_id,
        "name": name,
        "target_start": target_start,
        "target_end": target_end,
        "status": status, # Use API expected casing directly
    }
    # Add optional fields cleanly
    if lead_id is not None: data["lead"] = lead_id
    if description is not None: data["description"] = description
    if version is not None: data["version"] = version
    if build_id is not None: data["build_id"] = build_id
    if commit_hash is not None: data["commit_hash"] = commit_hash
    if branch_tag is not None: data["branch_tag"] = branch_tag
    if engagement_type is not None: data["engagement_type"] = engagement_type
    if deduplication_on_engagement is not None: data["deduplication_on_engagement"] = deduplication_on_engagement
    if tags is not None: data["tags"] = tags # Assumes API accepts list directly

    client = get_client()
    result = await client.create_engagement(data)

    # Return structured response
    if "error" in result:
        return {"status": "error", "error": result["error"], "details": result.get("details", "")}

    return {"status": "success", "data": result}


async def update_engagement(engagement_id: int, name: Optional[str] = None,
                           target_start: Optional[str] = None, # Renamed from start_date
                           target_end: Optional[str] = None,   # Renamed from end_date
                           status: Optional[str] = None,
                           description: Optional[str] = None,
                           # Add other updatable fields from API schema if needed
                           lead_id: Optional[int] = None,
                           version: Optional[str] = None,
                           build_id: Optional[str] = None,
                           commit_hash: Optional[str] = None,
                           branch_tag: Optional[str] = None,
                           engagement_type: Optional[str] = None,
                           deduplication_on_engagement: Optional[bool] = None,
                           tags: Optional[list] = None
                           ) -> Dict[str, Any]:
    """Update an existing engagement. Only provided fields are updated.

    Args:
        engagement_id: ID of the engagement to update.
        name: Optional new name.
        target_start: Optional new start date (YYYY-MM-DD).
        target_end: Optional new end date (YYYY-MM-DD).
        status: Optional new status ('Not Started', 'Blocked', 'Cancelled', 'Completed', 'In Progress', 'On Hold', 'Waiting for Resource').
        description: Optional new description.
        lead_id: Optional new lead ID.
        version: Optional new version.
        build_id: Optional new build ID.
        commit_hash: Optional new commit hash.
        branch_tag: Optional new branch/tag.
        engagement_type: Optional new engagement type ('Interactive', 'CI/CD').
        deduplication_on_engagement: Optional new deduplication setting.
        tags: Optional new list of tags (will replace existing tags).

    Returns:
        Dictionary with status and data/error.
    """
    # Validate status if provided
    if status:
        if status not in VALID_ENGAGEMENT_STATUSES:
            return {
                "status": "error",
                "error": (
                    f"Invalid status '{status}'. Must be one of: "
                    f"{', '.join(VALID_ENGAGEMENT_STATUSES)}"
                ),
            }

    # Validate engagement_type if provided
    if engagement_type and engagement_type not in ["Interactive", "CI/CD"]:
         return {"status": "error", "error": f"Invalid engagement_type '{engagement_type}'. Must be 'Interactive' or 'CI/CD'."}

    # Prepare data payload with only provided fields
    data = {}
    if name is not None: data["name"] = name
    if target_start is not None: data["target_start"] = target_start
    if target_end is not None: data["target_end"] = target_end
    if status is not None: data["status"] = status # Send as is after validation
    if description is not None: data["description"] = description
    if lead_id is not None: data["lead"] = lead_id
    if version is not None: data["version"] = version
    if build_id is not None: data["build_id"] = build_id
    if commit_hash is not None: data["commit_hash"] = commit_hash
    if branch_tag is not None: data["branch_tag"] = branch_tag
    if engagement_type is not None: data["engagement_type"] = engagement_type
    if deduplication_on_engagement is not None: data["deduplication_on_engagement"] = deduplication_on_engagement
    if tags is not None: data["tags"] = tags # PATCH usually replaces arrays

    # If no fields were provided, return an error
    if not data:
        return {"status": "error", "error": "At least one field must be provided for update"}

    client = get_client()
    result = await client.update_engagement(engagement_id, data)

    if "error" in result:
        return {"status": "error", "error": result["error"], "details": result.get("details", "")}

    return {"status": "success", "data": result}


async def close_engagement(engagement_id: int) -> Dict[str, Any]:
    """Close an engagement by setting its status to completed.

    Args:
        engagement_id: ID of the engagement to close

    Returns:
        Dictionary with status and data/error
    """
    # Use the specific status string from the API schema
    data = {
        "status": "Completed"
    }

    client = get_client()
    # Use the update_engagement client method
    result = await client.update_engagement(engagement_id, data)

    if "error" in result:
        return {"status": "error", "error": result["error"], "details": result.get("details", "")}

    # Check if the update was successful (API might return updated object or just status)
    # Assuming success if no error is present
    return {"status": "success", "data": result}


# --- Registration Function ---

def register_tools(mcp):
    """Register engagement-related tools with the MCP server instance."""
    mcp.tool(name="list_engagements", description="List engagements with optional filtering and pagination support")(list_engagements)
    mcp.tool(name="get_engagement", description="Get a specific engagement by ID")(get_engagement)
    mcp.tool(name="create_engagement", description="Create a new engagement")(create_engagement)
    mcp.tool(name="update_engagement", description="Update an existing engagement")(update_engagement)
    mcp.tool(name="close_engagement", description="Close an engagement")(close_engagement)
