"""Tests for engagements tools, including derived stale/recency filters."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, patch

import pytest

from defectdojo.engagements_tools import list_engagements


def _page(results: List[Dict[str, Any]], next_url: str | None = None) -> Dict[str, Any]:
    return {
        "count": len(results),
        "next": next_url,
        "previous": None,
        "results": results,
    }


class TestListEngagements:
    @pytest.mark.asyncio
    async def test_passthrough_filters_without_post_processing(self):
        client = AsyncMock()
        api_response = _page([{"id": 1, "name": "eng-1"}])
        client.get_engagements.return_value = api_response

        with patch("defectdojo.engagements_tools.get_client", return_value=client):
            result = await list_engagements(
                product_id=7,
                status="In Progress",
                name="gitlab",
                limit=5,
                offset=10,
            )

        assert result["status"] == "success"
        assert result["data"] == api_response
        call_filters = client.get_engagements.call_args[0][0]
        assert call_filters == {
            "o": "-updated",
            "product": 7,
            "status": "In Progress",
            "name": "gitlab",
            "limit": 5,
            "offset": 10,
        }

    @pytest.mark.asyncio
    async def test_invalid_status_is_rejected(self):
        result = await list_engagements(status="Open-ish")
        assert result["status"] == "error"
        assert "Invalid status filter" in result["error"]

    @pytest.mark.asyncio
    async def test_active_recent_days_filters_active_recent_only(self):
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(days=3)).isoformat()
        old = (now - timedelta(days=20)).isoformat()

        client = AsyncMock()
        client.get_engagements.return_value = _page(
            [
                {"id": 1, "active": True, "updated": recent, "status": "In Progress"},
                {"id": 2, "active": False, "updated": recent, "status": "In Progress"},
                {"id": 3, "active": True, "updated": old, "status": "In Progress"},
            ]
        )

        with patch("defectdojo.engagements_tools.get_client", return_value=client):
            result = await list_engagements(active_recent_days=14, limit=10)

        assert result["status"] == "success"
        assert [r["id"] for r in result["data"]["results"]] == [1]
        assert result["applied_filters"]["active_recent_days"] == 14

    @pytest.mark.asyncio
    async def test_overdue_days_filters_by_target_end(self):
        today = datetime.now(timezone.utc).date()
        overdue = (today - timedelta(days=10)).isoformat()
        not_overdue = (today - timedelta(days=2)).isoformat()

        client = AsyncMock()
        client.get_engagements.return_value = _page(
            [
                {"id": 10, "target_end": overdue, "status": "In Progress", "active": True},
                {"id": 11, "target_end": not_overdue, "status": "In Progress", "active": True},
            ]
        )

        with patch("defectdojo.engagements_tools.get_client", return_value=client):
            result = await list_engagements(overdue_days=7)

        assert result["status"] == "success"
        assert [r["id"] for r in result["data"]["results"]] == [10]
        assert result["applied_filters"]["overdue_days"] == 7

    @pytest.mark.asyncio
    async def test_stale_only_uses_default_thresholds(self):
        now = datetime.now(timezone.utc)
        old = (now - timedelta(days=20)).isoformat()
        recent = (now - timedelta(days=1)).isoformat()
        overdue = (now.date() - timedelta(days=10)).isoformat()
        fresh_due = (now.date() - timedelta(days=1)).isoformat()

        client = AsyncMock()
        client.get_engagements.return_value = _page(
            [
                {
                    "id": 21,
                    "active": True,
                    "status": "In Progress",
                    "updated": old,
                    "target_end": fresh_due,
                },
                {
                    "id": 22,
                    "active": True,
                    "status": "In Progress",
                    "updated": recent,
                    "target_end": overdue,
                },
                {
                    "id": 23,
                    "active": True,
                    "status": "In Progress",
                    "updated": recent,
                    "target_end": fresh_due,
                },
                {
                    "id": 24,
                    "active": True,
                    "status": "Not Started",
                    "updated": old,
                    "target_end": overdue,
                },
            ]
        )

        with patch("defectdojo.engagements_tools.get_client", return_value=client):
            result = await list_engagements(stale_only=True)

        assert result["status"] == "success"
        assert [r["id"] for r in result["data"]["results"]] == [21, 22]
        assert result["applied_filters"]["stale_only"] is True
        assert result["applied_filters"]["stale_recent_days"] == 14
        assert result["applied_filters"]["stale_overdue_days"] == 7

    @pytest.mark.asyncio
    async def test_post_filter_respects_limit_and_offset(self):
        now = datetime.now(timezone.utc)
        old = (now - timedelta(days=20)).isoformat()

        client = AsyncMock()
        client.get_engagements.side_effect = [
            _page(
                [
                    {"id": 31, "active": True, "status": "In Progress", "updated": old, "target_end": None},
                    {"id": 32, "active": True, "status": "In Progress", "updated": now.isoformat(), "target_end": None},
                ],
                next_url="next-page",
            ),
            _page(
                [
                    {"id": 33, "active": True, "status": "In Progress", "updated": old, "target_end": None},
                ]
            ),
        ]

        with patch("defectdojo.engagements_tools.get_client", return_value=client):
            result = await list_engagements(stale_only=True, limit=1, offset=1)

        assert result["status"] == "success"
        assert result["data"]["count"] == 2
        assert [r["id"] for r in result["data"]["results"]] == [33]
        assert result["data"]["previous"] is not None
        assert result["data"]["next"] is None

        first_call_filters = client.get_engagements.await_args_list[0].args[0]
        second_call_filters = client.get_engagements.await_args_list[1].args[0]
        assert first_call_filters["offset"] == 0
        assert second_call_filters["offset"] == 100

    @pytest.mark.asyncio
    async def test_post_filter_api_error_bubbles_up(self):
        client = AsyncMock()
        client.get_engagements.return_value = {"error": "HTTP error: 500", "details": "boom"}

        with patch("defectdojo.engagements_tools.get_client", return_value=client):
            result = await list_engagements(stale_only=True)

        assert result["status"] == "error"
        assert "500" in result["error"]

    @pytest.mark.asyncio
    async def test_legacy_filters_page_size_and_page_token_are_supported(self):
        client = AsyncMock()
        client.get_engagements.return_value = _page([{"id": 90, "status": "Completed"}])

        with patch("defectdojo.engagements_tools.get_client", return_value=client):
            result = await list_engagements(
                filters='{"status":"Completed"}',
                page_size="1",
                page_token="2",
            )

        assert result["status"] == "success"
        call_filters = client.get_engagements.call_args[0][0]
        assert call_filters == {
            "o": "-updated",
            "status": "Completed",
            "limit": 1,
            "offset": 2,
        }

    @pytest.mark.asyncio
    async def test_legacy_filters_dict_is_supported(self):
        client = AsyncMock()
        client.get_engagements.return_value = _page([{"id": 91, "status": "Completed"}])

        with patch("defectdojo.engagements_tools.get_client", return_value=client):
            result = await list_engagements(filters={"status": "Completed"}, page_size="1")

        assert result["status"] == "success"
        call_filters = client.get_engagements.call_args[0][0]
        assert call_filters["status"] == "Completed"
        assert call_filters["limit"] == 1

    @pytest.mark.asyncio
    async def test_legacy_stale_only_is_supported(self):
        now = datetime.now(timezone.utc)
        old = (now - timedelta(days=20)).isoformat()

        client = AsyncMock()
        client.get_engagements.return_value = _page(
            [
                {
                    "id": 101,
                    "active": True,
                    "status": "In Progress",
                    "updated": old,
                    "target_end": None,
                },
                {
                    "id": 102,
                    "active": True,
                    "status": "In Progress",
                    "updated": now.isoformat(),
                    "target_end": None,
                },
            ]
        )

        with patch("defectdojo.engagements_tools.get_client", return_value=client):
            result = await list_engagements(filters='{"stale_only":true}', page_size="1")

        assert result["status"] == "success"
        assert [r["id"] for r in result["data"]["results"]] == [101]
        assert result["applied_filters"]["stale_only"] is True

    @pytest.mark.asyncio
    async def test_invalid_legacy_filters_payload_is_rejected(self):
        result = await list_engagements(filters='{"status":"Completed"')
        assert result["status"] == "error"
        assert "JSON object string" in result["error"]
