"""Tests for newly added tools: get_finding, get_product, list_product_types, list_tests, get_test."""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest

from defectdojo.findings_tools import get_finding
from defectdojo.products_tools import get_product, list_product_types
from defectdojo.tests_tools import get_test, list_tests

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FINDING_RESPONSE: Dict[str, Any] = {
    "id": 702704,
    "title": "Potential Secret Found in Lambda",
    "severity": "Critical",
    "active": True,
    "verified": True,
}

PRODUCT_RESPONSE: Dict[str, Any] = {
    "id": 15,
    "name": "ciq-web",
    "prod_type": 7,
    "tags": ["full_sdlc"],
}

PRODUCT_TYPES_RESPONSE: Dict[str, Any] = {
    "count": 3,
    "next": None,
    "previous": None,
    "results": [
        {"id": 1, "name": "Web Applications"},
        {"id": 7, "name": "Docker Images"},
        {"id": 12, "name": "Infrastructure"},
    ],
}

TEST_RESPONSE: Dict[str, Any] = {
    "id": 18550,
    "title": "Prowler Scan",
    "test_type": 156,
    "engagement": 101,
}

TESTS_LIST_RESPONSE: Dict[str, Any] = {
    "count": 2,
    "next": None,
    "previous": None,
    "results": [
        {"id": 18550, "title": "Prowler Scan", "test_type": 156},
        {"id": 18551, "title": "Trivy Scan", "test_type": 120},
    ],
}

ERROR_RESPONSE: Dict[str, Any] = {
    "error": "HTTP error: 404",
    "details": "Not Found",
}


# ---------------------------------------------------------------------------
# get_finding
# ---------------------------------------------------------------------------


class TestGetFinding:
    """Tests for the get_finding tool function."""

    @pytest.mark.asyncio
    async def test_success(self):
        client = AsyncMock()
        client.get_finding.return_value = FINDING_RESPONSE
        with patch("defectdojo.findings_tools.get_client", return_value=client):
            result = await get_finding(finding_id=702704)

        assert result["status"] == "success"
        assert result["data"]["id"] == 702704
        assert result["data"]["severity"] == "Critical"
        client.get_finding.assert_awaited_once_with(702704)

    @pytest.mark.asyncio
    async def test_not_found(self):
        client = AsyncMock()
        client.get_finding.return_value = ERROR_RESPONSE
        with patch("defectdojo.findings_tools.get_client", return_value=client):
            result = await get_finding(finding_id=999999)

        assert result["status"] == "error"
        assert "404" in result["error"]


# ---------------------------------------------------------------------------
# get_product
# ---------------------------------------------------------------------------


class TestGetProduct:
    """Tests for the get_product tool function."""

    @pytest.mark.asyncio
    async def test_success(self):
        client = AsyncMock()
        client.get_product.return_value = PRODUCT_RESPONSE
        with patch("defectdojo.products_tools.get_client", return_value=client):
            result = await get_product(product_id=15)

        assert result["status"] == "success"
        assert result["data"]["name"] == "ciq-web"
        client.get_product.assert_awaited_once_with(15)

    @pytest.mark.asyncio
    async def test_not_found(self):
        client = AsyncMock()
        client.get_product.return_value = ERROR_RESPONSE
        with patch("defectdojo.products_tools.get_client", return_value=client):
            result = await get_product(product_id=999999)

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# list_product_types
# ---------------------------------------------------------------------------


class TestListProductTypes:
    """Tests for the list_product_types tool function."""

    @pytest.mark.asyncio
    async def test_no_filters(self):
        client = AsyncMock()
        client.get_product_types.return_value = PRODUCT_TYPES_RESPONSE
        with patch("defectdojo.products_tools.get_client", return_value=client):
            result = await list_product_types()

        assert result["status"] == "success"
        assert result["data"]["count"] == 3
        assert len(result["data"]["results"]) == 3
        assert "applied_filters" not in result

    @pytest.mark.asyncio
    async def test_name_filter(self):
        filtered = {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [{"id": 7, "name": "Docker Images"}],
        }
        client = AsyncMock()
        client.get_product_types.return_value = filtered
        with patch("defectdojo.products_tools.get_client", return_value=client):
            result = await list_product_types(name="Docker")

        assert result["status"] == "success"
        assert result["applied_filters"] == {"name": "Docker"}

    @pytest.mark.asyncio
    async def test_pagination(self):
        client = AsyncMock()
        client.get_product_types.return_value = PRODUCT_TYPES_RESPONSE
        with patch("defectdojo.products_tools.get_client", return_value=client):
            result = await list_product_types(limit=10, offset=20)

        assert result["status"] == "success"
        call_args = client.get_product_types.call_args[0][0]
        assert call_args["limit"] == 10
        assert call_args["offset"] == 20

    @pytest.mark.asyncio
    async def test_api_error(self):
        client = AsyncMock()
        client.get_product_types.return_value = ERROR_RESPONSE
        with patch("defectdojo.products_tools.get_client", return_value=client):
            result = await list_product_types()

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# list_tests
# ---------------------------------------------------------------------------


class TestListTests:
    """Tests for the list_tests tool function."""

    @pytest.mark.asyncio
    async def test_no_filters(self):
        client = AsyncMock()
        client.get_tests.return_value = TESTS_LIST_RESPONSE
        with patch("defectdojo.tests_tools.get_client", return_value=client):
            result = await list_tests()

        assert result["status"] == "success"
        assert result["data"]["count"] == 2
        assert "applied_filters" not in result

    @pytest.mark.asyncio
    async def test_engagement_filter(self):
        client = AsyncMock()
        client.get_tests.return_value = TESTS_LIST_RESPONSE
        with patch("defectdojo.tests_tools.get_client", return_value=client):
            result = await list_tests(engagement_id=101)

        assert result["status"] == "success"
        assert result["applied_filters"]["engagement"] == 101
        call_args = client.get_tests.call_args[0][0]
        assert call_args["engagement"] == 101

    @pytest.mark.asyncio
    async def test_test_type_filter(self):
        client = AsyncMock()
        client.get_tests.return_value = TESTS_LIST_RESPONSE
        with patch("defectdojo.tests_tools.get_client", return_value=client):
            result = await list_tests(test_type=156)

        assert result["status"] == "success"
        assert result["applied_filters"]["test_type"] == 156

    @pytest.mark.asyncio
    async def test_combined_filters(self):
        client = AsyncMock()
        client.get_tests.return_value = TESTS_LIST_RESPONSE
        with patch("defectdojo.tests_tools.get_client", return_value=client):
            result = await list_tests(engagement_id=101, test_type=156, tags="prowler")

        assert result["status"] == "success"
        applied = result["applied_filters"]
        assert applied["engagement"] == 101
        assert applied["test_type"] == 156
        assert applied["tags"] == "prowler"

    @pytest.mark.asyncio
    async def test_api_error(self):
        client = AsyncMock()
        client.get_tests.return_value = ERROR_RESPONSE
        with patch("defectdojo.tests_tools.get_client", return_value=client):
            result = await list_tests()

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# get_test
# ---------------------------------------------------------------------------


class TestGetTest:
    """Tests for the get_test tool function."""

    @pytest.mark.asyncio
    async def test_success(self):
        client = AsyncMock()
        client.get_test.return_value = TEST_RESPONSE
        with patch("defectdojo.tests_tools.get_client", return_value=client):
            result = await get_test(test_id=18550)

        assert result["status"] == "success"
        assert result["data"]["id"] == 18550
        client.get_test.assert_awaited_once_with(18550)

    @pytest.mark.asyncio
    async def test_not_found(self):
        client = AsyncMock()
        client.get_test.return_value = ERROR_RESPONSE
        with patch("defectdojo.tests_tools.get_client", return_value=client):
            result = await get_test(test_id=999999)

        assert result["status"] == "error"
