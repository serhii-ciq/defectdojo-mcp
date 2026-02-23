"""Tests for engagement_id filter in findings tools."""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest

from defectdojo.findings_tools import (
    _build_findings_filters,
    count_findings,
    get_findings,
    search_findings,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FINDINGS_LIST_RESPONSE: Dict[str, Any] = {
    "count": 42,
    "next": None,
    "previous": None,
    "results": [
        {
            "id": 730564,
            "title": "Potential Secret Found in Lambda",
            "severity": "Critical",
            "active": True,
            "test": 18550,
        },
    ],
}

ERROR_RESPONSE: Dict[str, Any] = {
    "error": "HTTP error: 400",
    "details": "Bad Request",
}


# ---------------------------------------------------------------------------
# _build_findings_filters
# ---------------------------------------------------------------------------


class TestBuildFindingsFilters:
    """Tests for the _build_findings_filters helper."""

    def test_no_engagement_id(self):
        filters = _build_findings_filters()
        assert "test__engagement" not in filters

    def test_engagement_id_set(self):
        filters = _build_findings_filters(engagement_id=17002)
        assert filters["test__engagement"] == 17002

    def test_engagement_id_combined_with_other_filters(self):
        filters = _build_findings_filters(
            engagement_id=17002,
            severity="Critical",
            active=True,
            product_name="ciq-tools",
        )
        assert filters["test__engagement"] == 17002
        assert filters["severity"] == "Critical"
        assert filters["active"] is True
        assert filters["product_name"] == "ciq-tools"

    def test_engagement_id_zero_is_passed(self):
        """Engagement ID of 0 is unlikely but should still be passed."""
        filters = _build_findings_filters(engagement_id=0)
        assert filters["test__engagement"] == 0

    def test_engagement_id_none_excluded(self):
        filters = _build_findings_filters(engagement_id=None)
        assert "test__engagement" not in filters


# ---------------------------------------------------------------------------
# get_findings with engagement_id
# ---------------------------------------------------------------------------


class TestGetFindingsEngagement:
    """Tests for get_findings with the engagement_id filter."""

    @pytest.mark.asyncio
    async def test_engagement_filter_applied(self):
        client = AsyncMock()
        client.get_findings.return_value = FINDINGS_LIST_RESPONSE
        with patch("defectdojo.findings_tools.get_client", return_value=client):
            result = await get_findings(engagement_id=17002)

        assert result["status"] == "success"
        assert result["applied_filters"]["test__engagement"] == 17002
        call_args = client.get_findings.call_args[0][0]
        assert call_args["test__engagement"] == 17002

    @pytest.mark.asyncio
    async def test_engagement_combined_with_severity(self):
        client = AsyncMock()
        client.get_findings.return_value = FINDINGS_LIST_RESPONSE
        with patch("defectdojo.findings_tools.get_client", return_value=client):
            result = await get_findings(engagement_id=17002, severity="Critical", active=True)

        assert result["status"] == "success"
        applied = result["applied_filters"]
        assert applied["test__engagement"] == 17002
        assert applied["severity"] == "Critical"
        assert applied["active"] is True

    @pytest.mark.asyncio
    async def test_no_engagement_filter(self):
        client = AsyncMock()
        client.get_findings.return_value = FINDINGS_LIST_RESPONSE
        with patch("defectdojo.findings_tools.get_client", return_value=client):
            result = await get_findings()

        assert result["status"] == "success"
        assert "applied_filters" not in result

    @pytest.mark.asyncio
    async def test_api_error(self):
        client = AsyncMock()
        client.get_findings.return_value = ERROR_RESPONSE
        with patch("defectdojo.findings_tools.get_client", return_value=client):
            result = await get_findings(engagement_id=17002)

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# search_findings with engagement_id
# ---------------------------------------------------------------------------


class TestSearchFindingsEngagement:
    """Tests for search_findings with the engagement_id filter."""

    @pytest.mark.asyncio
    async def test_engagement_filter_applied(self):
        client = AsyncMock()
        client.search_findings.return_value = FINDINGS_LIST_RESPONSE
        with patch("defectdojo.findings_tools.get_client", return_value=client):
            result = await search_findings(query="SQL Injection", engagement_id=17002)

        assert result["status"] == "success"
        applied = result["applied_filters"]
        assert applied["test__engagement"] == 17002
        assert applied["query"] == "SQL Injection"

    @pytest.mark.asyncio
    async def test_no_engagement_filter(self):
        client = AsyncMock()
        client.search_findings.return_value = FINDINGS_LIST_RESPONSE
        with patch("defectdojo.findings_tools.get_client", return_value=client):
            result = await search_findings(query="XSS")

        assert result["status"] == "success"
        assert "test__engagement" not in result.get("applied_filters", {})

    @pytest.mark.asyncio
    async def test_api_error(self):
        client = AsyncMock()
        client.search_findings.return_value = ERROR_RESPONSE
        with patch("defectdojo.findings_tools.get_client", return_value=client):
            result = await search_findings(query="test", engagement_id=17002)

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# count_findings with engagement_id
# ---------------------------------------------------------------------------


class TestCountFindingsEngagement:
    """Tests for count_findings with the engagement_id filter."""

    @pytest.mark.asyncio
    async def test_engagement_filter_applied(self):
        client = AsyncMock()
        client.get_findings.return_value = {"count": 42, "results": []}
        with patch("defectdojo.findings_tools.get_client", return_value=client):
            result = await count_findings(engagement_id=17002)

        assert result["status"] == "success"
        assert result["count"] == 42
        assert result["applied_filters"]["test__engagement"] == 17002

    @pytest.mark.asyncio
    async def test_engagement_combined_with_severity(self):
        client = AsyncMock()
        client.get_findings.return_value = {"count": 5, "results": []}
        with patch("defectdojo.findings_tools.get_client", return_value=client):
            result = await count_findings(engagement_id=17002, severity="Critical", active=True)

        assert result["status"] == "success"
        assert result["count"] == 5
        applied = result["applied_filters"]
        assert applied["test__engagement"] == 17002
        assert applied["severity"] == "Critical"
        assert applied["active"] is True

    @pytest.mark.asyncio
    async def test_no_engagement_filter(self):
        client = AsyncMock()
        client.get_findings.return_value = {"count": 100, "results": []}
        with patch("defectdojo.findings_tools.get_client", return_value=client):
            result = await count_findings()

        assert result["status"] == "success"
        assert result["count"] == 100
        assert "applied_filters" not in result

    @pytest.mark.asyncio
    async def test_uses_limit_1(self):
        """count_findings should use limit=1 to minimize payload."""
        client = AsyncMock()
        client.get_findings.return_value = {"count": 42, "results": []}
        with patch("defectdojo.findings_tools.get_client", return_value=client):
            await count_findings(engagement_id=17002)

        call_args = client.get_findings.call_args[0][0]
        assert call_args["limit"] == 1

    @pytest.mark.asyncio
    async def test_api_error(self):
        client = AsyncMock()
        client.get_findings.return_value = ERROR_RESPONSE
        with patch("defectdojo.findings_tools.get_client", return_value=client):
            result = await count_findings(engagement_id=17002)

        assert result["status"] == "error"
