import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import conversations as conv_repo
from app.db.session import get_db

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _msg_to_row(m) -> dict:
    if isinstance(m, HumanMessage):
        return {"role": "user", "content": _text(m.content)}
    if isinstance(m, AIMessage):
        return {"role": "assistant", "content": _text(m.content)}
    if isinstance(m, ToolMessage):
        return {"role": "tool", "content": _text(m.content), "name": m.name or ""}
    return {"role": getattr(m, "type", "unknown"), "content": _text(getattr(m, "content", ""))}


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
        return "".join(parts)
    return str(content)


@router.get("/{conversation_id}/messages")
async def list_messages(
    request: Request,
    conversation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise HTTPException(status_code=503, detail="agent not initialized")

    row = await conv_repo.get_conversation(session, conversation_id)
    if not row:
        raise HTTPException(status_code=404, detail="conversation not found")

    config = {"configurable": {"thread_id": str(conversation_id)}}
    snap = await graph.aget_state(config)
    if not snap or not snap.values:
        return []

    raw = snap.values.get("messages", [])
    out: list[dict] = []
    for m in raw:
        r = _msg_to_row(m)
        if r.get("role") == "tool":
            continue
        out.append({"role": r["role"], "content": r["content"]})
    return out
