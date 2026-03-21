from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import EmailAccountCreate
from app.config import get_settings
from app.db.models import EmailAccount, EmailSyncState
from app.email.crypto import encrypt_secret


async def list_accounts(session: AsyncSession) -> list[EmailAccount]:
    result = await session.execute(select(EmailAccount).order_by(EmailAccount.created_at.desc()))
    return list(result.scalars().all())


async def get_account(session: AsyncSession, account_id: uuid.UUID) -> EmailAccount | None:
    result = await session.execute(select(EmailAccount).where(EmailAccount.id == account_id))
    return result.scalar_one_or_none()


async def get_account_by_email_address(session: AsyncSession, email_address: str) -> EmailAccount | None:
    normalized = email_address.strip().lower()
    result = await session.execute(
        select(EmailAccount).where(func.lower(EmailAccount.email_address) == normalized)
    )
    return result.scalar_one_or_none()


async def get_sync_state(session: AsyncSession, account_id: uuid.UUID, folder_name: str = "INBOX") -> EmailSyncState | None:
    result = await session.execute(
        select(EmailSyncState).where(
            EmailSyncState.account_id == account_id,
            EmailSyncState.folder_name == folder_name,
        )
    )
    return result.scalar_one_or_none()


async def ensure_sync_state(session: AsyncSession, account_id: uuid.UUID, folder_name: str = "INBOX") -> EmailSyncState:
    row = await get_sync_state(session, account_id, folder_name=folder_name)
    if row is not None:
        return row

    row = EmailSyncState(
        account_id=account_id,
        folder_name=folder_name,
        next_check_at=datetime.now(UTC),
    )
    session.add(row)
    await session.flush()
    return row


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
    await session.flush()
    await ensure_sync_state(session, account.id)
    await session.commit()
    await session.refresh(account)
    return account


async def schedule_next_check(
    session: AsyncSession,
    account_id: uuid.UUID,
    *,
    next_check_at: datetime,
    folder_name: str = "INBOX",
) -> EmailSyncState:
    row = await ensure_sync_state(session, account_id, folder_name=folder_name)
    row.next_check_at = next_check_at
    await session.commit()
    await session.refresh(row)
    return row


async def mark_sync_started(
    session: AsyncSession,
    account_id: uuid.UUID,
    *,
    folder_name: str = "INBOX",
) -> EmailSyncState:
    row = await ensure_sync_state(session, account_id, folder_name=folder_name)
    row.last_check_started_at = datetime.now(UTC)
    row.last_error = ""
    await session.flush()
    return row


async def finalize_sync(
    session: AsyncSession,
    account: EmailAccount,
    *,
    uid_validity: int | None,
    last_seen_uid: int | None,
    error_message: str = "",
    folder_name: str = "INBOX",
) -> EmailSyncState:
    row = await ensure_sync_state(session, account.id, folder_name=folder_name)
    now = datetime.now(UTC)
    row.uid_validity = uid_validity
    row.last_seen_uid = last_seen_uid
    row.last_check_finished_at = now
    row.next_check_at = now + timedelta(minutes=account.poll_interval_minutes)
    row.last_error = error_message
    account.last_check_at = now
    await session.flush()
    return row


async def claim_due_account_ids(session: AsyncSession, *, limit: int, folder_name: str = "INBOX") -> list[uuid.UUID]:
    result = await session.execute(
        select(EmailSyncState.account_id)
        .join(EmailAccount, EmailAccount.id == EmailSyncState.account_id)
        .where(
            EmailAccount.enabled.is_(True),
            EmailSyncState.folder_name == folder_name,
            EmailSyncState.next_check_at.is_not(None),
            EmailSyncState.next_check_at <= func.now(),
        )
        .order_by(EmailSyncState.next_check_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    return list(result.scalars().all())
