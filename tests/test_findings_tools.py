"""Tests for finding tool functions (get_findings, search_findings, count_findings)."""

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

PAGINATED_RESPONSE: Dict[str, Any] = {
    "count": 5,
    "next": None,
    "previous": None,
    "results": [
        {"id": 1, "title": "XSS", "duplicate": False},
        {"id": 2, "title": "SQLi", "duplicate": False},
        {"id": 3, "title": "CSRF", "duplicate": True},
        {"id": 4, "title": "XSS dup", "duplicate": True},
        {"id": 5, "title": "SSRF", "duplicate": False},
    ],
}

ERROR_RESPONSE: Dict[str, Any] = {
    "error": "HTTP error: 500",
    "details": "Internal Server Error",
}


def _mock_client(
    get_response: Dict[str, Any] | None = None,
    search_response: Dict[str, Any] | None = None,
) -> AsyncMock:
    """Return a mock DefectDojoClient."""
    client = AsyncMock()
    client.get_findings.return_value = get_response or PAGINATED_RESPONSE
    client.search_findings.return_value = search_response or PAGINATED_RESPONSE
    return client


# ---------------------------------------------------------------------------
# _build_findings_filters – unit tests
# ---------------------------------------------------------------------------


class TestBuildFindingsFilters:
    """Unit tests for the internal filter builder."""

    def test_defaults(self):
        filters = _build_findings_filters()
        assert filters == {"limit": 20, "o": "id"}

    def test_product_name(self):
        filters = _build_findings_filters(product_name="MyApp")
        assert filters["product_name"] == "MyApp"

    def test_status(self):
        filters = _build_findings_filters(status="Active")
        assert filters["status"] == "Active"

    def test_severity(self):
        filters = _build_findings_filters(severity="High")
        assert filters["severity"] == "High"

    def test_duplicate_false(self):
        filters = _build_findings_filters(duplicate=False)
        assert filters["duplicate"] is False

    def test_duplicate_true(self):
        filters = _build_findings_filters(duplicate=True)
        assert filters["duplicate"] is True

    def test_duplicate_none_omitted(self):
        filters = _build_findings_filters(duplicate=None)
        assert "duplicate" not in filters

    def test_offset(self):
        filters = _build_findings_filters(offset=50)
        assert filters["offset"] == 50

    def test_combined(self):
        filters = _build_findings_filters(
            product_name="App",
            status="Active",
            severity="High",
            duplicate=False,
            limit=10,
            offset=20,
        )
        assert filters["product_name"] == "App"
        assert filters["status"] == "Active"
        assert filters["severity"] == "High"
        assert filters["duplicate"] is False
        assert filters["limit"] == 10
        assert filters["offset"] == 20
        assert filters["o"] == "id"

    def test_deterministic_ordering(self):
        filters = _build_findings_filters()
        assert filters["o"] == "id"


# ---------------------------------------------------------------------------
# get_findings – integration-style tests (mocked HTTP)
# ---------------------------------------------------------------------------


class TestGetFindings:
    """Tests for the get_findings tool function."""

    @pytest.mark.asyncio
    async def test_no_filters(self):
        mock = _mock_client()
        with patch("defectdojo.findings_tools.get_client", return_value=mock):
            result = await get_findings()

        assert result["status"] == "success"
        assert result["data"] == PAGINATED_RESPONSE
        assert "applied_filters" not in result

    @pytest.mark.asyncio
    async def test_duplicate_false(self):
        mock = _mock_client()
        with patch("defectdojo.findings_tools.get_client", return_value=mock):
            result = await get_findings(duplicate=False)

        assert result["status"] == "success"
        assert result["applied_filters"]["duplicate"] is False
        call_args = mock.get_findings.call_args[0][0]
        assert call_args["duplicate"] is False

    @pytest.mark.asyncio
    async def test_duplicate_true(self):
        mock = _mock_client()
        with patch("defectdojo.findings_tools.get_client", return_value=mock):
            result = await get_findings(duplicate=True)

        assert result["status"] == "success"
        assert result["applied_filters"]["duplicate"] is True

    @pytest.mark.asyncio
    async def test_combined_severity_status_duplicate(self):
        mock = _mock_client()
        with patch("defectdojo.findings_tools.get_client", return_value=mock):
            result = await get_findings(
                severity="High", status="Active", duplicate=False
            )

        assert result["status"] == "success"
        applied = result["applied_filters"]
        assert applied["severity"] == "High"
        assert applied["status"] == "Active"
        assert applied["duplicate"] is False

    @pytest.mark.asyncio
    async def test_api_error_propagated(self):
        mock = _mock_client(get_response=ERROR_RESPONSE)
        with patch("defectdojo.findings_tools.get_client", return_value=mock):
            result = await get_findings()

        assert result["status"] == "error"
        assert result["error"] == "HTTP error: 500"

    @pytest.mark.asyncio
    async def test_backward_compat_no_duplicate(self):
        """Existing callers that omit duplicate should still work."""
        mock = _mock_client()
        with patch("defectdojo.findings_tools.get_client", return_value=mock):
            result = await get_findings(product_name="Legacy", severity="Medium")

        assert result["status"] == "success"
        call_args = mock.get_findings.call_args[0][0]
        assert "duplicate" not in call_args
        assert call_args["product_name"] == "Legacy"
        assert call_args["severity"] == "Medium"

    @pytest.mark.asyncio
    async def test_deterministic_ordering(self):
        mock = _mock_client()
        with patch("defectdojo.findings_tools.get_client", return_value=mock):
            await get_findings()

        call_args = mock.get_findings.call_args[0][0]
        assert call_args["o"] == "id"


# ---------------------------------------------------------------------------
# search_findings – tests
# ---------------------------------------------------------------------------


class TestSearchFindings:
    """Tests for the search_findings tool function."""

    @pytest.mark.asyncio
    async def test_basic_search(self):
        mock = _mock_client()
        with patch("defectdojo.findings_tools.get_client", return_value=mock):
            result = await search_findings(query="XSS")

        assert result["status"] == "success"
        assert result["applied_filters"]["query"] == "XSS"

    @pytest.mark.asyncio
    async def test_search_with_duplicate_false(self):
        mock = _mock_client()
        with patch("defectdojo.findings_tools.get_client", return_value=mock):
            result = await search_findings(query="SQL", duplicate=False)

        assert result["status"] == "success"
        assert result["applied_filters"]["duplicate"] is False
        assert result["applied_filters"]["query"] == "SQL"

    @pytest.mark.asyncio
    async def test_search_api_error(self):
        mock = _mock_client(search_response=ERROR_RESPONSE)
        with patch("defectdojo.findings_tools.get_client", return_value=mock):
            result = await search_findings(query="test")

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# count_findings – integration-style tests (mocked HTTP)
# ---------------------------------------------------------------------------


class TestCountFindings:
    """Tests for the count_findings tool function."""

    @pytest.mark.asyncio
    async def test_count_no_filters(self):
        mock = _mock_client(get_response={"count": 100, "results": []})
        with patch("defectdojo.findings_tools.get_client", return_value=mock):
            result = await count_findings()

        assert result["status"] == "success"
        assert result["count"] == 100
        call_args = mock.get_findings.call_args[0][0]
        assert call_args["limit"] == 1

    @pytest.mark.asyncio
    async def test_count_duplicate_false(self):
        mock = _mock_client(get_response={"count": 42, "results": []})
        with patch("defectdojo.findings_tools.get_client", return_value=mock):
            result = await count_findings(duplicate=False)

        assert result["status"] == "success"
        assert result["count"] == 42
        assert result["applied_filters"]["duplicate"] is False

    @pytest.mark.asyncio
    async def test_count_duplicate_true(self):
        mock = _mock_client(get_response={"count": 58, "results": []})
        with patch("defectdojo.findings_tools.get_client", return_value=mock):
            result = await count_findings(duplicate=True)

        assert result["status"] == "success"
        assert result["count"] == 58
        assert result["applied_filters"]["duplicate"] is True

    @pytest.mark.asyncio
    async def test_count_combined_filters(self):
        mock = _mock_client(get_response={"count": 10, "results": []})
        with patch("defectdojo.findings_tools.get_client", return_value=mock):
            result = await count_findings(
                severity="High", status="Active", duplicate=False
            )

        assert result["status"] == "success"
        assert result["count"] == 10
        applied = result["applied_filters"]
        assert applied["severity"] == "High"
        assert applied["status"] == "Active"
        assert applied["duplicate"] is False

    @pytest.mark.asyncio
    async def test_count_matches_list(self):
        """count_findings total should equal get_findings count field."""
        payload = {
            "count": 15,
            "next": None,
            "previous": None,
            "results": [{"id": i} for i in range(15)],
        }
        mock_list = _mock_client(get_response=payload)
        mock_count = _mock_client(get_response={"count": 15, "results": []})

        with patch("defectdojo.findings_tools.get_client", return_value=mock_list):
            list_result = await get_findings(duplicate=False)
        with patch("defectdojo.findings_tools.get_client", return_value=mock_count):
            count_result = await count_findings(duplicate=False)

        assert list_result["data"]["count"] == count_result["count"]

    @pytest.mark.asyncio
    async def test_count_api_error(self):
        mock = _mock_client(get_response=ERROR_RESPONSE)
        with patch("defectdojo.findings_tools.get_client", return_value=mock):
            result = await count_findings()

        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_count_no_filters_no_applied_filters_key(self):
        mock = _mock_client(get_response={"count": 50, "results": []})
        with patch("defectdojo.findings_tools.get_client", return_value=mock):
            result = await count_findings()

        assert "applied_filters" not in result
