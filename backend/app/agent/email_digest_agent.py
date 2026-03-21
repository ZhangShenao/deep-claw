from __future__ import annotations

import json
import re
from typing import Any

from deepagents import create_deep_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.config import Settings

EMAIL_DIGEST_SYSTEM_PROMPT = (
    "你是 Deep-Claw 的 Email Sub-Agent。"
    "你的任务是分析一批刚同步到系统中的邮件，并输出结构化摘要。"
    "你必须先调用 get_email_batch_context 获取邮件内容。"
    "最终答案必须只输出一个 JSON 对象，不要输出额外解释。"
    'JSON 格式必须包含：summary(string), key_points(array), action_suggestions(array), priority(string)。'
    "不要编造不存在的邮件内容，不要输出 Markdown 代码块。"
)


def build_email_digest_agent(settings: Settings, email_batch: list[dict[str, Any]]):
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key or "placeholder",
        base_url=settings.openai_base_url,
        temperature=0.1,
    )

    @tool
    def get_email_batch_context() -> list[dict[str, Any]]:
        """Get the current batch of newly synced email messages for digest generation."""
        return email_batch

    return create_deep_agent(
        model=llm,
        system_prompt=EMAIL_DIGEST_SYSTEM_PROMPT,
        tools=[get_email_batch_context],
    )


def parse_email_digest_response(result: Any) -> dict[str, Any]:
    messages = result.get("messages") if isinstance(result, dict) else None
    if not messages:
        raise ValueError("email digest agent returned no messages")

    content = getattr(messages[-1], "content", messages[-1])
    if isinstance(content, list):
        text = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    else:
        text = str(content)

    text = text.strip()
    fenced = re.search(r"```json\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)

    data = json.loads(text)
    return {
        "summary": str(data.get("summary", "")),
        "key_points": data.get("key_points", []),
        "action_suggestions": data.get("action_suggestions", []),
        "priority": str(data.get("priority", "normal")),
    }
