"""Tests for user and group tools: list_users, get_user, list_dojo_groups, list_dojo_group_members."""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest

from defectdojo.users_tools import (
    get_user,
    list_dojo_group_members,
    list_dojo_groups,
    list_users,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_RESPONSE: Dict[str, Any] = {
    "id": 1,
    "username": "admin",
    "first_name": "Admin",
    "last_name": "User",
    "email": "admin@example.com",
    "is_active": True,
    "is_superuser": True,
}

USERS_LIST_RESPONSE: Dict[str, Any] = {
    "count": 3,
    "next": None,
    "previous": None,
    "results": [
        {"id": 1, "username": "admin", "is_active": True},
        {"id": 2, "username": "analyst", "is_active": True},
        {"id": 3, "username": "viewer", "is_active": False},
    ],
}

GROUP_RESPONSE: Dict[str, Any] = {
    "count": 2,
    "next": None,
    "previous": None,
    "results": [
        {"id": 1, "name": "AppSec Team"},
        {"id": 2, "name": "DevOps"},
    ],
}

GROUP_MEMBERS_RESPONSE: Dict[str, Any] = {
    "count": 2,
    "next": None,
    "previous": None,
    "results": [
        {"id": 10, "group": 1, "user": 1, "role": 4},
        {"id": 11, "group": 1, "user": 2, "role": 2},
    ],
}

ERROR_RESPONSE: Dict[str, Any] = {
    "error": "HTTP error: 404",
    "details": "Not Found",
}


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------


class TestListUsers:
    """Tests for the list_users tool function."""

    @pytest.mark.asyncio
    async def test_no_filters(self):
        client = AsyncMock()
        client.get_users.return_value = USERS_LIST_RESPONSE
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await list_users()

        assert result["status"] == "success"
        assert result["data"]["count"] == 3
        assert len(result["data"]["results"]) == 3
        assert "applied_filters" not in result

    @pytest.mark.asyncio
    async def test_username_filter(self):
        filtered = {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [{"id": 1, "username": "admin", "is_active": True}],
        }
        client = AsyncMock()
        client.get_users.return_value = filtered
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await list_users(username="admin")

        assert result["status"] == "success"
        assert result["applied_filters"] == {"username": "admin"}

    @pytest.mark.asyncio
    async def test_is_active_filter(self):
        client = AsyncMock()
        client.get_users.return_value = USERS_LIST_RESPONSE
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await list_users(is_active=True)

        assert result["status"] == "success"
        assert result["applied_filters"]["is_active"] is True
        call_args = client.get_users.call_args[0][0]
        assert call_args["is_active"] is True

    @pytest.mark.asyncio
    async def test_combined_filters(self):
        client = AsyncMock()
        client.get_users.return_value = USERS_LIST_RESPONSE
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await list_users(first_name="Admin", is_active=True, is_superuser=True)

        assert result["status"] == "success"
        applied = result["applied_filters"]
        assert applied["first_name"] == "Admin"
        assert applied["is_active"] is True
        assert applied["is_superuser"] is True

    @pytest.mark.asyncio
    async def test_pagination(self):
        client = AsyncMock()
        client.get_users.return_value = USERS_LIST_RESPONSE
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await list_users(limit=10, offset=20)

        assert result["status"] == "success"
        call_args = client.get_users.call_args[0][0]
        assert call_args["limit"] == 10
        assert call_args["offset"] == 20

    @pytest.mark.asyncio
    async def test_api_error(self):
        client = AsyncMock()
        client.get_users.return_value = ERROR_RESPONSE
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await list_users()

        assert result["status"] == "error"
        assert "404" in result["error"]


# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------


class TestGetUser:
    """Tests for the get_user tool function."""

    @pytest.mark.asyncio
    async def test_success(self):
        client = AsyncMock()
        client.get_user.return_value = USER_RESPONSE
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await get_user(user_id=1)

        assert result["status"] == "success"
        assert result["data"]["username"] == "admin"
        assert result["data"]["is_superuser"] is True
        client.get_user.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_not_found(self):
        client = AsyncMock()
        client.get_user.return_value = ERROR_RESPONSE
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await get_user(user_id=999999)

        assert result["status"] == "error"
        assert "404" in result["error"]


# ---------------------------------------------------------------------------
# list_dojo_groups
# ---------------------------------------------------------------------------


class TestListDojoGroups:
    """Tests for the list_dojo_groups tool function."""

    @pytest.mark.asyncio
    async def test_no_filters(self):
        client = AsyncMock()
        client.get_dojo_groups.return_value = GROUP_RESPONSE
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await list_dojo_groups()

        assert result["status"] == "success"
        assert result["data"]["count"] == 2
        assert len(result["data"]["results"]) == 2
        assert "applied_filters" not in result

    @pytest.mark.asyncio
    async def test_name_filter(self):
        filtered = {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [{"id": 1, "name": "AppSec Team"}],
        }
        client = AsyncMock()
        client.get_dojo_groups.return_value = filtered
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await list_dojo_groups(name="AppSec")

        assert result["status"] == "success"
        assert result["applied_filters"] == {"name": "AppSec"}

    @pytest.mark.asyncio
    async def test_pagination(self):
        client = AsyncMock()
        client.get_dojo_groups.return_value = GROUP_RESPONSE
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await list_dojo_groups(limit=5, offset=10)

        assert result["status"] == "success"
        call_args = client.get_dojo_groups.call_args[0][0]
        assert call_args["limit"] == 5
        assert call_args["offset"] == 10

    @pytest.mark.asyncio
    async def test_api_error(self):
        client = AsyncMock()
        client.get_dojo_groups.return_value = ERROR_RESPONSE
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await list_dojo_groups()

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# list_dojo_group_members
# ---------------------------------------------------------------------------


class TestListDojoGroupMembers:
    """Tests for the list_dojo_group_members tool function."""

    @pytest.mark.asyncio
    async def test_no_filters(self):
        client = AsyncMock()
        client.get_dojo_group_members.return_value = GROUP_MEMBERS_RESPONSE
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await list_dojo_group_members()

        assert result["status"] == "success"
        assert result["data"]["count"] == 2
        assert "applied_filters" not in result

    @pytest.mark.asyncio
    async def test_group_filter(self):
        client = AsyncMock()
        client.get_dojo_group_members.return_value = GROUP_MEMBERS_RESPONSE
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await list_dojo_group_members(group_id=1)

        assert result["status"] == "success"
        assert result["applied_filters"]["group"] == 1
        call_args = client.get_dojo_group_members.call_args[0][0]
        assert call_args["group"] == 1

    @pytest.mark.asyncio
    async def test_user_filter(self):
        client = AsyncMock()
        client.get_dojo_group_members.return_value = GROUP_MEMBERS_RESPONSE
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await list_dojo_group_members(user_id=2)

        assert result["status"] == "success"
        assert result["applied_filters"]["user"] == 2

    @pytest.mark.asyncio
    async def test_combined_filters(self):
        client = AsyncMock()
        client.get_dojo_group_members.return_value = GROUP_MEMBERS_RESPONSE
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await list_dojo_group_members(group_id=1, user_id=2)

        assert result["status"] == "success"
        applied = result["applied_filters"]
        assert applied["group"] == 1
        assert applied["user"] == 2

    @pytest.mark.asyncio
    async def test_pagination(self):
        client = AsyncMock()
        client.get_dojo_group_members.return_value = GROUP_MEMBERS_RESPONSE
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await list_dojo_group_members(limit=10, offset=5)

        assert result["status"] == "success"
        call_args = client.get_dojo_group_members.call_args[0][0]
        assert call_args["limit"] == 10
        assert call_args["offset"] == 5

    @pytest.mark.asyncio
    async def test_api_error(self):
        client = AsyncMock()
        client.get_dojo_group_members.return_value = ERROR_RESPONSE
        with patch("defectdojo.users_tools.get_client", return_value=client):
            result = await list_dojo_group_members()

        assert result["status"] == "error"
