from typing import Any, Dict, List, Optional, Union
from defectdojo.client import get_client

# --- Product Tool Definitions ---

VALID_TAGS_MODES = ("any", "all")


def _build_product_filters(
    *,
    name: Optional[str] = None,
    prod_type: Optional[Union[int, List[int]]] = None,
    tags: Optional[Union[str, List[str]]] = None,
    tags_mode: Optional[str] = None,
    external_audience: Optional[bool] = None,
    internet_accessible: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """Build a query-parameter dict accepted by the DefectDojo products API.

    DefectDojo v2 API supports the following query parameters for
    ``/api/v2/products/``:

    * ``name`` – exact or substring match
    * ``prod_type`` – product-type id (repeatable)
    * ``tags`` – tag name (repeatable)
    * ``not_tags`` – exclude tag (repeatable)
    * ``external_audience`` – boolean
    * ``internet_accessible`` – boolean
    * ``o`` – ordering field (e.g. ``id``)
    * ``limit`` / ``offset`` – pagination

    When *tags_mode* is ``"all"`` (default) each tag is sent as a separate
    ``tags`` query param – the API intersects them.  When *tags_mode* is
    ``"any"`` we use the ``tag`` parameter which does an OR match.
    """
    filters: Dict[str, Any] = {
        "limit": limit,
        "o": "id",  # deterministic ordering
    }

    if name:
        filters["name"] = name

    # prod_type – accept single int or list of ints
    if prod_type is not None:
        filters["prod_type"] = prod_type

    # tags
    if tags is not None:
        effective_mode = (tags_mode or "all").lower()
        if effective_mode not in VALID_TAGS_MODES:
            raise ValueError(
                f"Invalid tags_mode '{tags_mode}'. Must be one of: {', '.join(VALID_TAGS_MODES)}"
            )
        tag_list = [tags] if isinstance(tags, str) else list(tags)
        if effective_mode == "all":
            filters["tags"] = tag_list
        else:
            # "any" – use the 'tag' param which does OR matching
            filters["tag"] = tag_list

    if external_audience is not None:
        filters["external_audience"] = external_audience

    if internet_accessible is not None:
        filters["internet_accessible"] = internet_accessible

    if offset:
        filters["offset"] = offset

    return filters


async def list_products(
    name: Optional[str] = None,
    prod_type: Optional[Union[int, List[int]]] = None,
    tags: Optional[Union[str, List[str]]] = None,
    tags_mode: Optional[str] = None,
    external_audience: Optional[bool] = None,
    internet_accessible: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """List all products with optional filtering and pagination support.

    Args:
        name: Optional name filter (partial match).
        prod_type: Optional product type ID filter (int or list of ints).
        tags: Optional tag(s) to filter by – a single tag string or a list.
        tags_mode: How to combine multiple tags: ``"all"`` (AND, default)
            or ``"any"`` (OR).
        external_audience: Filter by external-audience flag.
        internet_accessible: Filter by internet-accessible flag.
        limit: Maximum number of products to return per page (default: 50).
        offset: Number of records to skip (default: 0).

    Returns:
        Dictionary with status, data/error, and pagination metadata.
    """
    try:
        filters = _build_product_filters(
            name=name,
            prod_type=prod_type,
            tags=tags,
            tags_mode=tags_mode,
            external_audience=external_audience,
            internet_accessible=internet_accessible,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}

    client = get_client()
    result = await client.get_products(filters)

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


async def count_products(
    name: Optional[str] = None,
    prod_type: Optional[Union[int, List[int]]] = None,
    tags: Optional[Union[str, List[str]]] = None,
    tags_mode: Optional[str] = None,
    external_audience: Optional[bool] = None,
    internet_accessible: Optional[bool] = None,
) -> Dict[str, Any]:
    """Return the total number of products matching the given filters.

    This is a lightweight alternative to ``list_products`` when you only
    need the count.  It requests a single record (``limit=1``) and reads
    the ``count`` field from the paginated response.

    Args:
        name: Optional name filter (partial match).
        prod_type: Optional product type ID filter (int or list of ints).
        tags: Optional tag(s) to filter by – a single tag string or a list.
        tags_mode: How to combine multiple tags: ``"all"`` (AND, default)
            or ``"any"`` (OR).
        external_audience: Filter by external-audience flag.
        internet_accessible: Filter by internet-accessible flag.

    Returns:
        Dictionary with status and total count.
    """
    try:
        filters = _build_product_filters(
            name=name,
            prod_type=prod_type,
            tags=tags,
            tags_mode=tags_mode,
            external_audience=external_audience,
            internet_accessible=internet_accessible,
            limit=1,  # minimize payload – we only need the count
            offset=0,
        )
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}

    client = get_client()
    result = await client.get_products(filters)

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


# --- Registration Function ---


def register_tools(mcp):
    """Register product-related tools with the MCP server instance."""
    mcp.tool(
        name="list_products",
        description="List all products with optional filtering and pagination support",
    )(list_products)
    mcp.tool(
        name="count_products",
        description="Return total number of products matching the given filters (lightweight, no full payload)",
    )(count_products)
