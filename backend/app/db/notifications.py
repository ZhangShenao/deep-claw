from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Notification


async def list_notifications(session: AsyncSession) -> list[Notification]:
    result = await session.execute(select(Notification).order_by(Notification.created_at.desc()))
    return list(result.scalars().all())


async def create_notification(
    session: AsyncSession,
    *,
    notification_type: str,
    account_id,
    digest_id,
    title: str,
    body: str,
) -> Notification:
    row = Notification(
        type=notification_type,
        account_id=account_id,
        digest_id=digest_id,
        title=title,
        body=body,
    )
    session.add(row)
    await session.flush()
    return row


async def get_notification(session: AsyncSession, notification_id) -> Notification | None:
    result = await session.execute(select(Notification).where(Notification.id == notification_id))
    return result.scalar_one_or_none()


async def mark_notification_read(session: AsyncSession, notification: Notification) -> Notification:
    notification.is_read = True
    await session.commit()
    await session.refresh(notification)
    return notification
