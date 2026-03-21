from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Notification


async def list_notifications(session: AsyncSession) -> list[Notification]:
    result = await session.execute(select(Notification).order_by(Notification.created_at.desc()))
    return list(result.scalars().all())
