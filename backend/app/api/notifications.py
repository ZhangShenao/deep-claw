from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import NotificationOut
from app.db import notifications as notifications_repo
from app.db.session import get_db as db_session_dep

router = APIRouter(tags=["notifications"])
get_db = db_session_dep


@router.get("/api/notifications", response_model=list[NotificationOut])
async def list_notifications(session: AsyncSession = Depends(get_db)) -> list[NotificationOut]:
    rows = await notifications_repo.list_notifications(session)
    return [NotificationOut.model_validate(row) for row in rows]
