"""Map LangGraph astream_events (v2) to SSE payloads."""

import json
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessageChunk
from langgraph.graph.state import CompiledStateGraph


def _json_safe(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in list(obj.items())[:50]}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj[:50]]
    if isinstance(obj, AIMessageChunk):
        return {"content": getattr(obj, "content", "")}
    mod = type(obj).__module__
    if mod.startswith("langchain") or mod.startswith("pydantic"):
        try:
            if hasattr(obj, "model_dump"):
                return _json_safe(obj.model_dump())
        except Exception:
            pass
    return str(obj)[:2000]


def _extract_chunk_text(chunk: Any) -> str:
    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
        return "".join(parts)
    return ""


async def map_graph_events(
    graph: CompiledStateGraph,
    payload: dict[str, Any],
    config: dict[str, Any],
) -> AsyncIterator[str]:
    """Yield SSE lines `data: {...}\\n\\n`."""
    async for ev in graph.astream_events(payload, config, version="v2"):
        et = ev.get("event")
        name = ev.get("name") or ""
        data = ev.get("data") or {}

        if et == "on_chat_model_stream":
            chunk = data.get("chunk")
            text = _extract_chunk_text(chunk) if chunk is not None else ""
            if text:
                yield f"data: {json.dumps({'type': 'token', 'content': text}, ensure_ascii=False)}\n\n"
            continue

        if et == "on_tool_start":
            tool_name = name.split(":")[-1] if ":" in name else name
            inp = data.get("input")
            if tool_name == "task" or "task" in tool_name.lower():
                yield f"data: {json.dumps({'type': 'subagent', 'phase': 'start', 'name': _json_safe(inp)}, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'tool_start', 'name': tool_name, 'input': _json_safe(inp)}, ensure_ascii=False)}\n\n"
            continue

        if et == "on_tool_end":
            tool_name = name.split(":")[-1] if ":" in name else name
            out = data.get("output")
            if tool_name == "task" or "task" in tool_name.lower():
                yield f"data: {json.dumps({'type': 'subagent', 'phase': 'end', 'name': tool_name, 'output': _json_safe(out)}, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'tool_end', 'name': tool_name, 'output': _json_safe(out)}, ensure_ascii=False)}\n\n"
            continue
