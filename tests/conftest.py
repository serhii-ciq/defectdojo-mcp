"""Shared test fixtures for DefectDojo MCP tests."""

import os
import pytest


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    """Ensure required environment variables are set for all tests."""
    monkeypatch.setenv("DEFECTDOJO_API_BASE", "https://defectdojo.example.com")
    monkeypatch.setenv("DEFECTDOJO_API_TOKEN", "test-token")
