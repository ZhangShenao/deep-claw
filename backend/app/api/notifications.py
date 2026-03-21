import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import NotificationOut
from app.db import notifications as notifications_repo
from app.db.session import get_db as db_session_dep
from app.db.session import get_session

router = APIRouter(tags=["notifications"])
get_db = db_session_dep


@router.get("/api/notifications", response_model=list[NotificationOut])
async def list_notifications(session: AsyncSession = Depends(get_db)) -> list[NotificationOut]:
    rows = await notifications_repo.list_notifications(session)
    return [NotificationOut.model_validate(row) for row in rows]


@router.patch("/api/notifications/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_read(
    notification_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> NotificationOut:
    row = await notifications_repo.get_notification(session, notification_id)
    if row is None:
        raise HTTPException(status_code=404, detail="notification not found")

    updated = await notifications_repo.mark_notification_read(session, row)
    return NotificationOut.model_validate(updated)


@router.get("/api/notifications/stream")
async def stream_notifications() -> StreamingResponse:
    async def gen():
        sent_ids: set[str] = set()
        while True:
            async with get_session() as session:
                rows = await notifications_repo.list_notifications(session)

            fresh_rows = []
            for row in reversed(rows):
                row_id = str(row.id)
                if row_id in sent_ids:
                    continue
                fresh_rows.append(row)
                sent_ids.add(row_id)

            if fresh_rows:
                for row in fresh_rows:
                    payload = {
                        "type": "notification",
                        "id": str(row.id),
                        "notification_type": row.type,
                        "title": row.title,
                        "body": row.body,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                        "payload": {
                            "digest_id": str(row.digest_id) if row.digest_id else None,
                            "account_id": str(row.account_id) if row.account_id else None,
                        },
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'heartbeat'}, ensure_ascii=False)}\n\n"

            await asyncio.sleep(2)

    return StreamingResponse(gen(), media_type="text/event-stream")
