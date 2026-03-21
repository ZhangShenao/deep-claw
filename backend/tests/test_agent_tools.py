from __future__ import annotations

from dataclasses import dataclass

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools import build_run_email_check_tool
from app.api.schemas import EmailAccountCreate
from app.db import email_accounts as email_accounts_repo


@dataclass
class FakeEmailCheckResult:
    digest_id: str
    account_id: str
    trigger_source: str
    new_message_count: int
    summary: str


@pytest.mark.asyncio
async def test_run_email_check_tool_accepts_email_address(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = await email_accounts_repo.create_account(
        db_session,
        EmailAccountCreate(
            email_address="user@example.com",
            provider_label="Example",
            imap_host="imap.example.com",
            imap_port=993,
            credential="secret",
            poll_interval_minutes=15,
        ),
    )

    async def fake_run_manual_email_check(session, account_id):  # noqa: ANN001
        assert str(account_id) == str(account.id)
        return FakeEmailCheckResult(
            digest_id="digest-1",
            account_id=str(account.id),
            trigger_source="manual",
            new_message_count=1,
            summary="summary",
        )

    monkeypatch.setattr("app.agent.tools.run_manual_email_check", fake_run_manual_email_check)

    tool = build_run_email_check_tool()
    result = await tool.ainvoke({"account_id": "user@example.com"})

    assert result["account_id"] == str(account.id)
    assert result["summary"] == "summary"


@pytest.mark.asyncio
async def test_run_email_check_tool_falls_back_to_only_connected_account(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = await email_accounts_repo.create_account(
        db_session,
        EmailAccountCreate(
            email_address="real-user@example.com",
            provider_label="Example",
            imap_host="imap.example.com",
            imap_port=993,
            credential="secret",
            poll_interval_minutes=15,
        ),
    )

    async def fake_run_manual_email_check(session, account_id):  # noqa: ANN001
        assert str(account_id) == str(account.id)
        return FakeEmailCheckResult(
            digest_id="digest-2",
            account_id=str(account.id),
            trigger_source="manual",
            new_message_count=1,
            summary="fallback summary",
        )

    monkeypatch.setattr("app.agent.tools.run_manual_email_check", fake_run_manual_email_check)

    tool = build_run_email_check_tool()
    result = await tool.ainvoke({"account_id": "hallucinated@163.com"})

    assert result["account_id"] == str(account.id)
    assert result["summary"] == "fallback summary"
