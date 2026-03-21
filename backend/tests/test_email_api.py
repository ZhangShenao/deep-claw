"""Email feature API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_email_accounts_initially_empty(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/email/accounts")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_email_account(async_client: AsyncClient) -> None:
    payload = {
        "email_address": "user@example.com",
        "provider_label": "Example",
        "imap_host": "imap.example.com",
        "imap_port": 993,
        "auth_type": "app_password",
        "credential": "secret",
        "poll_interval_minutes": 15,
    }
    response = await async_client.post("/api/email/accounts", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["email_address"] == "user@example.com"
    assert body["provider_label"] == "Example"
    assert body["enabled"] is True

    response = await async_client.get("/api/email/accounts")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["email_address"] == "user@example.com"


@pytest.mark.asyncio
async def test_list_notifications_initially_empty(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/notifications")
    assert response.status_code == 200
    assert response.json() == []
