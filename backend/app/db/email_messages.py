from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EmailDigest, EmailMessage


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
