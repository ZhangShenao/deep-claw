"""Email feature API tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EmailAccount, EmailMessage


@dataclass
class FakeValidatedImapClient:
    validated: list[str]

    async def validate_connection(
        self,
        *,
        host: str,
        port: int,
        username: str,
        credential: str,
        folder_name: str,
    ) -> None:
        self.validated.append(username)


@pytest.fixture(autouse=True)
def fake_imap_validation(monkeypatch: pytest.MonkeyPatch) -> FakeValidatedImapClient:
    client = FakeValidatedImapClient(validated=[])
    monkeypatch.setattr("app.api.email.build_imap_client", lambda: client)
    return client


@pytest.mark.asyncio
async def test_list_email_accounts_initially_empty(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/email/accounts")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_email_account(
    async_client: AsyncClient,
    fake_imap_validation: FakeValidatedImapClient,
) -> None:
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
    assert fake_imap_validation.validated == ["user@example.com"]


@pytest.mark.asyncio
async def test_list_notifications_initially_empty(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/notifications")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_check_now_creates_digest_and_notification(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    account = EmailAccount(
        email_address="digest@example.com",
        provider_label="Digest",
        imap_host="imap.example.com",
        imap_port=993,
        credential_encrypted="stored",
    )
    db_session.add(account)
    await db_session.flush()

    db_session.add(
        EmailMessage(
            account_id=account.id,
            folder_name="INBOX",
            message_uid=1,
            from_display="Alice",
            from_address="alice@example.com",
            subject="Need budget review",
            snippet="Please review the budget sheet today.",
            body_text="Please review the budget sheet today.",
        )
    )
    await db_session.commit()

    response = await async_client.post(f"/api/email/accounts/{account.id}/check-now")
    assert response.status_code == 200
    body = response.json()
    assert body["trigger_source"] == "manual"
    assert body["new_message_count"] == 1
    assert body["summary"]

    response = await async_client.get("/api/email/digests")
    assert response.status_code == 200
    digests = response.json()
    assert len(digests) == 1
    assert digests[0]["account_id"] == str(account.id)

    response = await async_client.get("/api/notifications")
    assert response.status_code == 200
    notifications = response.json()
    assert len(notifications) == 1
    assert notifications[0]["type"] == "email_digest_ready"
