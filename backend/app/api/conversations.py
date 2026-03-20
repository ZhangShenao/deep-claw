import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ConversationCreate, ConversationOut
from app.db import conversations as conv_repo
from app.db.session import get_db as db_session_dep

router = APIRouter(prefix="/api/conversations", tags=["conversations"])
get_db = db_session_dep


@router.get("", response_model=list[ConversationOut])
async def list_conversations(session: AsyncSession = Depends(get_db)) -> list[ConversationOut]:
    rows = await conv_repo.list_conversations(session)
    return [ConversationOut.model_validate(r) for r in rows]


@router.post("", response_model=ConversationOut)
async def create_conversation(
    body: ConversationCreate,
    session: AsyncSession = Depends(get_db),
) -> ConversationOut:
    row = await conv_repo.create_conversation(session, title=body.title)
    return ConversationOut.model_validate(row)


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    from sqlalchemy import delete

    from app.db.models import Conversation

    row = await conv_repo.get_conversation(session, conversation_id)
    if not row:
        raise HTTPException(status_code=404, detail="conversation not found")
    await session.execute(delete(Conversation).where(Conversation.id == conversation_id))
    await session.commit()
