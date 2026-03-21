from __future__ import annotations

import uuid
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EmailDigest, EmailMessage
from app.email.client import ImapMessageEnvelope
from app.email.parser import normalize_email_message


async def list_messages_for_account(session: AsyncSession, account_id: uuid.UUID) -> list[EmailMessage]:
    result = await session.execute(
        select(EmailMessage)
        .where(EmailMessage.account_id == account_id)
        .order_by(EmailMessage.received_at.desc().nullslast(), EmailMessage.ingested_at.desc())
    )
    return list(result.scalars().all())


async def list_digests(session: AsyncSession) -> list[EmailDigest]:
    result = await session.execute(select(EmailDigest).order_by(EmailDigest.created_at.desc()))
    return list(result.scalars().all())


async def store_fetched_messages(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    folder_name: str,
    envelopes: Iterable[ImapMessageEnvelope],
) -> list[EmailMessage]:
    stored: list[EmailMessage] = []

    for envelope in envelopes:
        existing_result = await session.execute(
            select(EmailMessage).where(
                EmailMessage.account_id == account_id,
                EmailMessage.folder_name == folder_name,
                EmailMessage.message_uid == envelope.uid,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            continue

        normalized = normalize_email_message(envelope.raw_message)
        row = EmailMessage(
            account_id=account_id,
            folder_name=folder_name,
            message_uid=envelope.uid,
            message_id_header=normalized.message_id_header,
            from_display=normalized.from_display,
            from_address=normalized.from_address,
            subject=normalized.subject,
            received_at=normalized.received_at,
            is_unread="\\Seen" not in envelope.flags,
            snippet=normalized.snippet,
            body_text=normalized.body_text,
        )
        session.add(row)
        await session.flush()
        stored.append(row)

    return stored
