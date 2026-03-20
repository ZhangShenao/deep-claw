import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation


async def list_conversations(session: AsyncSession) -> list[Conversation]:
    result = await session.execute(select(Conversation).order_by(Conversation.updated_at.desc()))
    return list(result.scalars().all())


async def get_conversation(session: AsyncSession, cid: uuid.UUID) -> Conversation | None:
    result = await session.execute(select(Conversation).where(Conversation.id == cid))
    return result.scalar_one_or_none()


async def create_conversation(session: AsyncSession, title: str | None = None) -> Conversation:
    conv = Conversation(title=title or "新对话")
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv


async def touch_conversation(session: AsyncSession, cid: uuid.UUID) -> None:
    await session.execute(
        update(Conversation).where(Conversation.id == cid).values(updated_at=func.now())
    )
    await session.commit()


async def update_title(session: AsyncSession, cid: uuid.UUID, title: str) -> None:
    await session.execute(update(Conversation).where(Conversation.id == cid).values(title=title))
    await session.commit()
