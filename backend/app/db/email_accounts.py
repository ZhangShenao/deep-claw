from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import EmailAccountCreate
from app.config import get_settings
from app.db.models import EmailAccount
from app.email.crypto import encrypt_secret


async def list_accounts(session: AsyncSession) -> list[EmailAccount]:
    result = await session.execute(select(EmailAccount).order_by(EmailAccount.created_at.desc()))
    return list(result.scalars().all())


async def get_account(session: AsyncSession, account_id: uuid.UUID) -> EmailAccount | None:
    result = await session.execute(select(EmailAccount).where(EmailAccount.id == account_id))
    return result.scalar_one_or_none()


async def create_account(session: AsyncSession, body: EmailAccountCreate) -> EmailAccount:
    settings = get_settings()
    account = EmailAccount(
        email_address=body.email_address,
        provider_label=body.provider_label,
        imap_host=body.imap_host,
        imap_port=body.imap_port,
        imap_security=body.imap_security,
        auth_type=body.auth_type,
        credential_encrypted=encrypt_secret(body.credential, settings),
        poll_interval_minutes=body.poll_interval_minutes,
        enabled=body.enabled,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account
