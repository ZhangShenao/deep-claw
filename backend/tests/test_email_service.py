"""Email service unit tests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import EmailAccountCreate
from app.config import get_settings
from app.db import email_accounts as email_accounts_repo
from app.db.models import EmailDigest, EmailMessage
from app.email.client import ImapFetchResult, ImapMessageEnvelope
from app.email.crypto import decrypt_secret, encrypt_secret
from app.email.parser import normalize_email_message
from app.email.service import run_scheduled_email_check
from app.email.worker import run_due_account_checks_once


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


@dataclass
class FakeImapClient:
    fetch_result: ImapFetchResult
    validated: list[str]

    async def validate_connection(self, *, host: str, port: int, username: str, credential: str, folder_name: str) -> None:
        self.validated.append(username)

    async def fetch_new_messages(
        self,
        *,
        host: str,
        port: int,
        username: str,
        credential: str,
        folder_name: str,
        last_seen_uid: int | None,
    ) -> ImapFetchResult:
        return self.fetch_result


@dataclass
class FakeDigestAgent:
    response_content: str
    payloads: list[dict]

    async def ainvoke(self, payload: dict) -> dict:
        self.payloads.append(payload)
        return {"messages": [SimpleNamespace(content=self.response_content)]}


def _raw_email(subject: str, body: str, *, sender: str = "alice@example.com", msg_id: str = "msg-1") -> bytes:
    return (
        f"From: Alice <{sender}>\r\n"
        "To: User <user@example.com>\r\n"
        f"Subject: {subject}\r\n"
        "Date: Sat, 21 Mar 2026 12:00:00 +0000\r\n"
        f"Message-ID: <{msg_id}@example.com>\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        f"{body}\r\n"
    ).encode("utf-8")


@pytest.mark.asyncio
async def test_run_scheduled_email_check_fetches_and_persists_new_messages(db_session: AsyncSession) -> None:
    payload = EmailAccountCreate(
        email_address=f"{uuid.uuid4()}@example.com",
        provider_label="Example",
        imap_host="imap.example.com",
        imap_port=993,
        credential="super-secret",
        poll_interval_minutes=15,
    )
    account = await email_accounts_repo.create_account(db_session, payload)

    fake_client = FakeImapClient(
        fetch_result=ImapFetchResult(
            uid_validity=777,
            messages=[
                ImapMessageEnvelope(uid=11, raw_message=_raw_email("Budget review", "Please review the budget sheet today."), flags=[]),
                ImapMessageEnvelope(uid=12, raw_message=_raw_email("Contract follow-up", "Need your approval before 5pm.", msg_id="msg-2"), flags=["\\Seen"]),
            ],
        ),
        validated=[],
    )

    result = await run_scheduled_email_check(db_session, account.id, imap_client=fake_client)

    assert result.trigger_source == "scheduled"
    assert result.new_message_count == 2
    assert fake_client.validated == []

    messages = await db_session.execute(
        EmailMessage.__table__.select().where(EmailMessage.account_id == account.id)
    )
    assert len(messages.all()) == 2

    digests = await db_session.execute(EmailDigest.__table__.select().where(EmailDigest.account_id == account.id))
    assert len(digests.all()) == 1

    sync_state = await email_accounts_repo.get_sync_state(db_session, account.id)
    assert sync_state is not None
    assert sync_state.uid_validity == 777
    assert sync_state.last_seen_uid == 12
    assert sync_state.last_check_finished_at is not None
    assert sync_state.next_check_at is not None


@pytest.mark.asyncio
async def test_run_scheduled_email_check_uses_digest_agent_output(db_session: AsyncSession) -> None:
    payload = EmailAccountCreate(
        email_address=f"{uuid.uuid4()}@example.com",
        provider_label="Example",
        imap_host="imap.example.com",
        imap_port=993,
        credential="super-secret",
        poll_interval_minutes=15,
    )
    account = await email_accounts_repo.create_account(db_session, payload)

    fake_client = FakeImapClient(
        fetch_result=ImapFetchResult(
            uid_validity=888,
            messages=[
                ImapMessageEnvelope(
                    uid=31,
                    raw_message=_raw_email("Escalation", "Please reply before noon.", msg_id="msg-31"),
                    flags=[],
                ),
            ],
        ),
        validated=[],
    )
    fake_agent = FakeDigestAgent(
        response_content='{"summary":"Agent summary","key_points":[{"subject":"Escalation"}],"action_suggestions":[{"action":"Reply now","reason":"deadline before noon"}],"priority":"high"}',
        payloads=[],
    )

    result = await run_scheduled_email_check(
        db_session,
        account.id,
        imap_client=fake_client,
        digest_agent=fake_agent,
    )

    assert result.summary == "Agent summary"
    assert len(fake_agent.payloads) == 1

    digests = await db_session.execute(EmailDigest.__table__.select().where(EmailDigest.account_id == account.id))
    row = digests.first()
    assert row is not None
    assert row.summary == "Agent summary"


@pytest.mark.asyncio
async def test_run_due_account_checks_once_processes_only_due_accounts(db_session: AsyncSession) -> None:
    due_account = await email_accounts_repo.create_account(
        db_session,
        EmailAccountCreate(
            email_address=f"{uuid.uuid4()}@example.com",
            provider_label="Due",
            imap_host="imap.example.com",
            imap_port=993,
            credential="secret-1",
            poll_interval_minutes=15,
        ),
    )
    later_account = await email_accounts_repo.create_account(
        db_session,
        EmailAccountCreate(
            email_address=f"{uuid.uuid4()}@example.com",
            provider_label="Later",
            imap_host="imap.example.com",
            imap_port=993,
            credential="secret-2",
            poll_interval_minutes=15,
        ),
    )

    await email_accounts_repo.schedule_next_check(
        db_session,
        due_account.id,
        next_check_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    await email_accounts_repo.schedule_next_check(
        db_session,
        later_account.id,
        next_check_at=datetime.now(UTC) + timedelta(hours=1),
    )

    fake_client = FakeImapClient(
        fetch_result=ImapFetchResult(
            uid_validity=900,
            messages=[
                ImapMessageEnvelope(uid=21, raw_message=_raw_email("Due task", "This account should be processed.", msg_id="msg-3"), flags=[]),
            ],
        ),
        validated=[],
    )

    processed = await run_due_account_checks_once(db_session, imap_client=fake_client, limit=10)

    assert processed == 1

    due_sync = await email_accounts_repo.get_sync_state(db_session, due_account.id)
    later_sync = await email_accounts_repo.get_sync_state(db_session, later_account.id)
    assert due_sync is not None and due_sync.last_seen_uid == 21
    assert later_sync is not None and later_sync.last_seen_uid is None
