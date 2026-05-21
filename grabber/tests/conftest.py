"""Shared fixtures for grabber tests."""
import json
from pathlib import Path

import pytest


@pytest.fixture
def sample_session():
    """Realistic session JSON từ /api/auth/session (sanitized)."""
    return {
        "user": {
            "id": "user-abc123",
            "name": "Test User",
            "email": "test@example.com",
            "idp": "auth0",
            "mfa": True,
        },
        "expires": "2026-08-19T02:22:38.295Z",
        "account": {
            "id": "11111111-2222-3333-4444-555555555555",
            "planType": "plus",
        },
        # JWT payload decoded: { "exp": 9999999999, "client_id": "app_X8zY6vW2pQ9tR3dE7nK1jL5gH",
        #                       "https://api.openai.com/profile": {"email": "test@example.com"} }
        "accessToken": "eyJhbGciOiJSUzI1NiJ9.eyJleHAiOjk5OTk5OTk5OTksImNsaWVudF9pZCI6ImFwcF9YOHpZNnZXMnBROXRSM2RFN25LMWpMNWdIIiwiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS9wcm9maWxlIjp7ImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSJ9fQ.sig",
        "authProvider": "openai",
        "sessionToken": "encrypted-jwe-string",
    }
