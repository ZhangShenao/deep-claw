from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import EmailAccountCreate
from app.db.models import EmailAccount


async def list_accounts(session: AsyncSession) -> list[EmailAccount]:
    result = await session.execute(select(EmailAccount).order_by(EmailAccount.created_at.desc()))
    return list(result.scalars().all())


async def create_account(session: AsyncSession, body: EmailAccountCreate) -> EmailAccount:
    account = EmailAccount(
        email_address=body.email_address,
        provider_label=body.provider_label,
        imap_host=body.imap_host,
        imap_port=body.imap_port,
        imap_security=body.imap_security,
        auth_type=body.auth_type,
        credential_encrypted=body.credential,
        poll_interval_minutes=body.poll_interval_minutes,
        enabled=body.enabled,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account
