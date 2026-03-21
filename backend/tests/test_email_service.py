"""Email service unit tests."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import EmailAccountCreate
from app.config import get_settings
from app.db import email_accounts as email_accounts_repo
from app.email.crypto import decrypt_secret, encrypt_secret
from app.email.parser import normalize_email_message


def test_encrypt_round_trip() -> None:
    settings = get_settings()
    token = encrypt_secret("app-password", settings)
    assert decrypt_secret(token, settings) == "app-password"


def test_normalize_email_message_trims_quotes() -> None:
    raw_email = (
        b"From: Alice <alice@example.com>\r\n"
        b"To: User <user@example.com>\r\n"
        b"Subject: Weekly update\r\n"
        b"Date: Sat, 21 Mar 2026 12:00:00 +0000\r\n"
        b"Message-ID: <msg-1@example.com>\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"\r\n"
        b"Hi team,\r\n\r\n"
        b"Please review the budget sheet today.\r\n\r\n"
        b"On Tue, someone wrote:\r\n"
        b"> quoted line\r\n"
    )

    normalized = normalize_email_message(raw_email)

    assert normalized.subject == "Weekly update"
    assert "Please review the budget sheet today." in normalized.body_text
    assert "On Tue, someone wrote:" not in normalized.body_text


@pytest.mark.asyncio
async def test_create_account_encrypts_credential(db_session: AsyncSession) -> None:
    payload = EmailAccountCreate(
        email_address=f"{uuid.uuid4()}@example.com",
        provider_label="Example",
        imap_host="imap.example.com",
        imap_port=993,
        credential="super-secret",
        poll_interval_minutes=15,
    )

    account = await email_accounts_repo.create_account(db_session, payload)

    assert account.credential_encrypted != "super-secret"
    assert decrypt_secret(account.credential_encrypted, get_settings()) == "super-secret"
