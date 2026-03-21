from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from app.agent.email_digest_agent import build_email_digest_agent, parse_email_digest_response
from app.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import email_accounts as email_accounts_repo
from app.db import email_messages as email_messages_repo
from app.db import notifications as notifications_repo
from app.db.models import EmailDigest
from app.email.client import ImapClient, ImapClientProtocol
from app.email.crypto import decrypt_secret


@dataclass(slots=True)
class EmailCheckResult:
    digest_id: uuid.UUID | None
    account_id: uuid.UUID
    trigger_source: str
    new_message_count: int
    summary: str


class EmailDigestAgentProtocol(Protocol):
    async def ainvoke(self, payload: dict[str, Any]) -> dict[str, Any]: ...


def _build_summary(messages) -> tuple[str, list[dict], list[dict], str]:
    if not messages:
        return (
            "没有检测到可总结的新邮件。",
            [],
            [{"action": "无需处理", "reason": "当前没有已同步邮件"}],
            "low",
        )

    top_subjects = [message.subject or "无主题" for message in messages[:3]]
    summary = f"最近共有 {len(messages)} 封已同步邮件，重点包括：{'；'.join(top_subjects)}。"
    key_points = [
        {
            "from": message.from_address or message.from_display,
            "subject": message.subject,
            "snippet": message.snippet,
        }
        for message in messages[:3]
    ]
    actions = [
        {
            "action": f"优先处理《{message.subject or '无主题'}》",
            "reason": message.snippet or "这封邮件出现在最新邮件摘要中。",
        }
        for message in messages[:3]
    ]
    return summary, key_points, actions, "normal"


def _serialize_messages_for_agent(messages) -> list[dict[str, Any]]:
    return [
        {
            "message_id": str(message.id),
            "from_display": message.from_display,
            "from_address": message.from_address,
            "subject": message.subject,
            "snippet": message.snippet,
            "body_text": message.body_text,
            "received_at": message.received_at.isoformat() if message.received_at else None,
            "is_unread": message.is_unread,
        }
        for message in messages
    ]


async def _generate_digest_via_agent(
    messages,
    *,
    digest_agent: EmailDigestAgentProtocol | None = None,
) -> tuple[str, list[dict], list[dict], str]:
    if not messages:
        return _build_summary(messages)

    agent = digest_agent or build_email_digest_agent(get_settings(), _serialize_messages_for_agent(messages))
    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "分析这批最新同步的邮件，输出 summary、key_points、action_suggestions、priority 的 JSON。",
                }
            ]
        }
    )
    parsed = parse_email_digest_response(result)
    return (
        parsed["summary"],
        parsed["key_points"],
        parsed["action_suggestions"],
        parsed["priority"],
    )


def build_imap_client() -> ImapClientProtocol:
    settings = get_settings()
    return ImapClient(timeout_seconds=settings.email_imap_timeout_seconds)


async def _create_digest_and_notification(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    email_address: str,
    trigger_source: str,
    digest_scope: str,
    messages,
    create_notification: bool,
    digest_content: tuple[str, list[dict], list[dict], str] | None = None,
) -> EmailDigest:
    summary, key_points, actions, priority = digest_content or _build_summary(messages)

    digest = EmailDigest(
        account_id=account_id,
        trigger_source=trigger_source,
        digest_scope=digest_scope,
        message_ids=[str(message.id) for message in messages],
        summary=summary,
        key_points_json=key_points,
        action_suggestions_json=actions,
        priority=priority,
    )
    session.add(digest)
    await session.flush()

    if create_notification:
        await notifications_repo.create_notification(
            session,
            notification_type="email_digest_ready",
            account_id=account_id,
            digest_id=digest.id,
            title=f"{email_address} 邮件摘要已生成",
            body=summary,
        )

    return digest


async def run_manual_email_check(
    session: AsyncSession,
    account_id: uuid.UUID,
    *,
    digest_agent: EmailDigestAgentProtocol | None = None,
) -> EmailCheckResult:
    account = await email_accounts_repo.get_account(session, account_id)
    if account is None:
        raise LookupError("email account not found")

    messages = await email_messages_repo.list_messages_for_account(session, account_id)
    try:
        digest_content = await _generate_digest_via_agent(
            messages,
            digest_agent=digest_agent,
        )
    except Exception:
        digest_content = _build_summary(messages)
    digest = await _create_digest_and_notification(
        session,
        account_id=account_id,
        email_address=account.email_address,
        trigger_source="manual",
        digest_scope="all_synced_messages",
        messages=messages,
        create_notification=True,
        digest_content=digest_content,
    )
    summary = digest.summary

    await session.commit()

    return EmailCheckResult(
        digest_id=digest.id,
        account_id=account_id,
        trigger_source="manual",
        new_message_count=len(messages),
        summary=summary,
    )


async def run_scheduled_email_check(
    session: AsyncSession,
    account_id: uuid.UUID,
    *,
    imap_client: ImapClientProtocol | None = None,
    digest_agent: EmailDigestAgentProtocol | None = None,
) -> EmailCheckResult:
    account = await email_accounts_repo.get_account(session, account_id)
    if account is None:
        raise LookupError("email account not found")

    client = imap_client or build_imap_client()
    sync_state = await email_accounts_repo.mark_sync_started(session, account.id)
    credential = decrypt_secret(account.credential_encrypted, get_settings())

    try:
        fetch_result = await client.fetch_new_messages(
            host=account.imap_host,
            port=account.imap_port,
            username=account.email_address,
            credential=credential,
            folder_name=sync_state.folder_name,
            last_seen_uid=sync_state.last_seen_uid,
        )

        if (
            sync_state.uid_validity is not None
            and fetch_result.uid_validity is not None
            and sync_state.uid_validity != fetch_result.uid_validity
        ):
            fetch_result = await client.fetch_new_messages(
                host=account.imap_host,
                port=account.imap_port,
                username=account.email_address,
                credential=credential,
                folder_name=sync_state.folder_name,
                last_seen_uid=None,
            )

        stored_messages = await email_messages_repo.store_fetched_messages(
            session,
            account_id=account.id,
            folder_name=sync_state.folder_name,
            envelopes=fetch_result.messages,
        )

        last_seen_uid = sync_state.last_seen_uid
        if fetch_result.messages:
            last_seen_uid = max(message.uid for message in fetch_result.messages)

        digest_id: uuid.UUID | None = None
        summary = "没有检测到新的邮件。"
        if stored_messages:
            try:
                digest_content = await _generate_digest_via_agent(
                    stored_messages,
                    digest_agent=digest_agent,
                )
            except Exception:
                digest_content = _build_summary(stored_messages)
            digest = await _create_digest_and_notification(
                session,
                account_id=account.id,
                email_address=account.email_address,
                trigger_source="scheduled",
                digest_scope="new_messages_since_cursor",
                messages=stored_messages,
                create_notification=True,
                digest_content=digest_content,
            )
            digest_id = digest.id
            summary = digest.summary

        await email_accounts_repo.finalize_sync(
            session,
            account,
            uid_validity=fetch_result.uid_validity,
            last_seen_uid=last_seen_uid,
            error_message="",
            folder_name=sync_state.folder_name,
        )
        await session.commit()
        return EmailCheckResult(
            digest_id=digest_id,
            account_id=account.id,
            trigger_source="scheduled",
            new_message_count=len(stored_messages),
            summary=summary,
        )
    except Exception as exc:
        await email_accounts_repo.finalize_sync(
            session,
            account,
            uid_validity=sync_state.uid_validity,
            last_seen_uid=sync_state.last_seen_uid,
            error_message=str(exc),
            folder_name=sync_state.folder_name,
        )
        await session.commit()
        raise
