from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import email_accounts as email_accounts_repo
from app.db import email_messages as email_messages_repo
from app.db import notifications as notifications_repo
from app.db.models import EmailDigest


@dataclass(slots=True)
class EmailCheckResult:
    digest_id: uuid.UUID
    account_id: uuid.UUID
    trigger_source: str
    new_message_count: int
    summary: str


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


async def run_manual_email_check(session: AsyncSession, account_id: uuid.UUID) -> EmailCheckResult:
    account = await email_accounts_repo.get_account(session, account_id)
    if account is None:
        raise LookupError("email account not found")

    messages = await email_messages_repo.list_messages_for_account(session, account_id)
    summary, key_points, actions, priority = _build_summary(messages)

    digest = EmailDigest(
        account_id=account_id,
        trigger_source="manual",
        digest_scope="all_synced_messages",
        message_ids=[str(message.id) for message in messages],
        summary=summary,
        key_points_json=key_points,
        action_suggestions_json=actions,
        priority=priority,
    )
    session.add(digest)
    await session.flush()

    await notifications_repo.create_notification(
        session,
        notification_type="email_digest_ready",
        account_id=account_id,
        digest_id=digest.id,
        title=f"{account.email_address} 邮件摘要已生成",
        body=summary,
    )

    await session.commit()

    return EmailCheckResult(
        digest_id=digest.id,
        account_id=account_id,
        trigger_source="manual",
        new_message_count=len(messages),
        summary=summary,
    )
