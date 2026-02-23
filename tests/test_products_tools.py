"""Tests for product tool functions (list_products, count_products)."""

from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, patch

import pytest

from defectdojo.products_tools import (
    _build_product_filters,
    count_products,
    list_products,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PAGINATED_RESPONSE: Dict[str, Any] = {
    "count": 3,
    "next": None,
    "previous": None,
    "results": [
        {"id": 1, "name": "Product A", "tags": ["full_sdlc"]},
        {"id": 2, "name": "Product B", "tags": ["full_sdlc", "cloud"]},
        {"id": 3, "name": "Product C", "tags": []},
    ],
}

ERROR_RESPONSE: Dict[str, Any] = {
    "error": "HTTP error: 500",
    "details": "Internal Server Error",
}


def _mock_client(response: Dict[str, Any]) -> AsyncMock:
    """Return a mock DefectDojoClient whose get_products returns *response*."""
    client = AsyncMock()
    client.get_products.return_value = response
    return client


# ---------------------------------------------------------------------------
# _build_product_filters – unit tests
# ---------------------------------------------------------------------------


class TestBuildProductFilters:
    """Unit tests for the internal filter builder."""

    def test_defaults(self):
        filters = _build_product_filters()
        assert filters == {"limit": 50, "o": "id"}

    def test_name_filter(self):
        filters = _build_product_filters(name="Foo")
        assert filters["name"] == "Foo"

    def test_prod_type_single(self):
        filters = _build_product_filters(prod_type=5)
        assert filters["prod_type"] == 5

    def test_prod_type_list(self):
        filters = _build_product_filters(prod_type=[1, 2])
        assert filters["prod_type"] == [1, 2]

    def test_tags_single_string_defaults_to_all(self):
        filters = _build_product_filters(tags="full_sdlc")
        assert filters["tags"] == ["full_sdlc"]
        assert "tag" not in filters

    def test_tags_list_all_mode(self):
        filters = _build_product_filters(tags=["a", "b"], tags_mode="all")
        assert filters["tags"] == ["a", "b"]
        assert "tag" not in filters

    def test_tags_any_mode(self):
        filters = _build_product_filters(tags=["a", "b"], tags_mode="any")
        assert filters["tag"] == ["a", "b"]
        assert "tags" not in filters

    def test_tags_mode_case_insensitive(self):
        filters = _build_product_filters(tags="x", tags_mode="ANY")
        assert "tag" in filters

    def test_tags_mode_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid tags_mode"):
            _build_product_filters(tags="x", tags_mode="invalid")

    def test_external_audience_true(self):
        filters = _build_product_filters(external_audience=True)
        assert filters["external_audience"] is True

    def test_external_audience_false(self):
        filters = _build_product_filters(external_audience=False)
        assert filters["external_audience"] is False

    def test_internet_accessible(self):
        filters = _build_product_filters(internet_accessible=True)
        assert filters["internet_accessible"] is True

    def test_offset(self):
        filters = _build_product_filters(offset=100)
        assert filters["offset"] == 100

    def test_combined_filters(self):
        filters = _build_product_filters(
            name="Prod",
            prod_type=3,
            tags=["full_sdlc"],
            external_audience=True,
            internet_accessible=False,
            limit=10,
            offset=20,
        )
        assert filters["name"] == "Prod"
        assert filters["prod_type"] == 3
        assert filters["tags"] == ["full_sdlc"]
        assert filters["external_audience"] is True
        assert filters["internet_accessible"] is False
        assert filters["limit"] == 10
        assert filters["offset"] == 20
        assert filters["o"] == "id"


# ---------------------------------------------------------------------------
# list_products – integration-style tests (mocked HTTP)
# ---------------------------------------------------------------------------


class TestListProducts:
    """Tests for the list_products tool function."""

    @pytest.mark.asyncio
    async def test_no_filters(self):
        mock = _mock_client(PAGINATED_RESPONSE)
        with patch("defectdojo.products_tools.get_client", return_value=mock):
            result = await list_products()

        assert result["status"] == "success"
        assert result["data"] == PAGINATED_RESPONSE
        # No user-provided filters → no applied_filters key
        assert "applied_filters" not in result
        mock.get_products.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_with_tags_filter(self):
        mock = _mock_client(PAGINATED_RESPONSE)
        with patch("defectdojo.products_tools.get_client", return_value=mock):
            result = await list_products(tags="full_sdlc")

        assert result["status"] == "success"
        assert result["applied_filters"] == {"tags": ["full_sdlc"]}
        # Verify the client was called with expected params
        call_args = mock.get_products.call_args[0][0]
        assert call_args["tags"] == ["full_sdlc"]

    @pytest.mark.asyncio
    async def test_with_external_audience_filter(self):
        mock = _mock_client(PAGINATED_RESPONSE)
        with patch("defectdojo.products_tools.get_client", return_value=mock):
            result = await list_products(external_audience=True)

        assert result["status"] == "success"
        assert result["applied_filters"]["external_audience"] is True

    @pytest.mark.asyncio
    async def test_combined_filters(self):
        mock = _mock_client(PAGINATED_RESPONSE)
        with patch("defectdojo.products_tools.get_client", return_value=mock):
            result = await list_products(
                tags=["full_sdlc", "cloud"],
                external_audience=True,
                prod_type=2,
            )

        assert result["status"] == "success"
        applied = result["applied_filters"]
        assert applied["tags"] == ["full_sdlc", "cloud"]
        assert applied["external_audience"] is True
        assert applied["prod_type"] == 2

    @pytest.mark.asyncio
    async def test_invalid_tags_mode(self):
        result = await list_products(tags="x", tags_mode="bad")
        assert result["status"] == "error"
        assert "Invalid tags_mode" in result["error"]

    @pytest.mark.asyncio
    async def test_api_error_propagated(self):
        mock = _mock_client(ERROR_RESPONSE)
        with patch("defectdojo.products_tools.get_client", return_value=mock):
            result = await list_products()

        assert result["status"] == "error"
        assert result["error"] == "HTTP error: 500"

    @pytest.mark.asyncio
    async def test_backward_compat_name_and_prod_type(self):
        """Existing callers that only pass name/prod_type should still work."""
        mock = _mock_client(PAGINATED_RESPONSE)
        with patch("defectdojo.products_tools.get_client", return_value=mock):
            result = await list_products(name="Legacy", prod_type=1)

        assert result["status"] == "success"
        call_args = mock.get_products.call_args[0][0]
        assert call_args["name"] == "Legacy"
        assert call_args["prod_type"] == 1

    @pytest.mark.asyncio
    async def test_deterministic_ordering(self):
        """Verify that ordering param is always sent."""
        mock = _mock_client(PAGINATED_RESPONSE)
        with patch("defectdojo.products_tools.get_client", return_value=mock):
            await list_products()

        call_args = mock.get_products.call_args[0][0]
        assert call_args["o"] == "id"


# ---------------------------------------------------------------------------
# count_products – integration-style tests (mocked HTTP)
# ---------------------------------------------------------------------------


class TestCountProducts:
    """Tests for the count_products tool function."""

    @pytest.mark.asyncio
    async def test_count_no_filters(self):
        mock = _mock_client({"count": 42, "results": []})
        with patch("defectdojo.products_tools.get_client", return_value=mock):
            result = await count_products()

        assert result["status"] == "success"
        assert result["count"] == 42
        # With limit=1 to minimize payload
        call_args = mock.get_products.call_args[0][0]
        assert call_args["limit"] == 1

    @pytest.mark.asyncio
    async def test_count_with_tags(self):
        mock = _mock_client({"count": 7, "results": []})
        with patch("defectdojo.products_tools.get_client", return_value=mock):
            result = await count_products(tags="full_sdlc")

        assert result["status"] == "success"
        assert result["count"] == 7
        assert result["applied_filters"] == {"tags": ["full_sdlc"]}

    @pytest.mark.asyncio
    async def test_count_with_combined_filters(self):
        mock = _mock_client({"count": 2, "results": []})
        with patch("defectdojo.products_tools.get_client", return_value=mock):
            result = await count_products(
                tags="full_sdlc",
                external_audience=True,
                prod_type=3,
            )

        assert result["status"] == "success"
        assert result["count"] == 2
        applied = result["applied_filters"]
        assert "tags" in applied
        assert applied["external_audience"] is True
        assert applied["prod_type"] == 3

    @pytest.mark.asyncio
    async def test_count_matches_list(self):
        """count_products total should equal list_products count field."""
        payload = {
            "count": 5,
            "next": None,
            "previous": None,
            "results": [{"id": i} for i in range(5)],
        }
        mock_list = _mock_client(payload)
        mock_count = _mock_client({"count": 5, "results": []})

        with patch("defectdojo.products_tools.get_client", return_value=mock_list):
            list_result = await list_products(tags="full_sdlc")
        with patch("defectdojo.products_tools.get_client", return_value=mock_count):
            count_result = await count_products(tags="full_sdlc")

        assert list_result["data"]["count"] == count_result["count"]

    @pytest.mark.asyncio
    async def test_count_api_error(self):
        mock = _mock_client(ERROR_RESPONSE)
        with patch("defectdojo.products_tools.get_client", return_value=mock):
            result = await count_products()

        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_count_invalid_tags_mode(self):
        result = await count_products(tags="x", tags_mode="nope")
        assert result["status"] == "error"
        assert "Invalid tags_mode" in result["error"]

    @pytest.mark.asyncio
    async def test_count_no_filters_no_applied_filters_key(self):
        mock = _mock_client({"count": 10, "results": []})
        with patch("defectdojo.products_tools.get_client", return_value=mock):
            result = await count_products()

        assert "applied_filters" not in result
