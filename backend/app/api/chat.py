import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ChatStreamIn
from app.config import get_settings
from app.db import conversations as conv_repo
from app.db.session import get_db
from app.streaming import map_graph_events

router = APIRouter(tags=["chat"])


@router.post("/api/chat/stream")
async def chat_stream(
    request: Request,
    body: ChatStreamIn,
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise HTTPException(status_code=503, detail="agent not initialized")

    row = await conv_repo.get_conversation(session, body.thread_id)
    if not row:
        raise HTTPException(status_code=404, detail="conversation not found")

    if row.title in ("", "新对话"):
        title = body.message.strip().replace("\n", " ")[:80] or "新对话"
        await conv_repo.update_title(session, body.thread_id, title)
    else:
        await conv_repo.touch_conversation(session, body.thread_id)

    payload = {"messages": [HumanMessage(content=body.message)]}
    settings = get_settings()
    config: dict = {
        "configurable": {"thread_id": str(body.thread_id)},
        "recursion_limit": settings.langgraph_recursion_limit,
    }

    thread_id_str = str(body.thread_id)

    async def gen():
        try:
            async for line in map_graph_events(graph, payload, config):
                yield line
            yield f"data: {json.dumps({'type': 'done', 'thread_id': thread_id_str}, ensure_ascii=False)}\n\n"
        except Exception as e:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
