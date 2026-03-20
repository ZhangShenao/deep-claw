from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver

from deepagents import create_deep_agent

from app.agent.tools import build_internet_search
from app.config import Settings


def build_deep_agent(settings: Settings, checkpointer: BaseCheckpointSaver):
    """Compile Deep Agent with Mongo checkpointer and a research sub-agent."""

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key or "placeholder",
        base_url=settings.openai_base_url,
        temperature=0.2,
    )

    internet_search = build_internet_search(settings)

    research_subagent = {
        "name": "research",
        "description": (
            "用于深度网络调研：多关键词检索、对比来源、输出结构化摘要与要点。"
            "当用户需要最新网页信息、行业数据、新闻或引用来源时使用。"
        ),
        "system_prompt": (
            "你是深度调研助手。仅使用提供的 internet_search 工具获取网络信息；"
            "综合多轮检索结果，用中文输出：摘要、分点要点、并注明信息局限。"
            "不要编造 URL 或引用。"
        ),
        "tools": [internet_search],
    }

    system_prompt = (
        "你是 Deep-Claw 个人助理，帮助用户完成日常对话与任务编排。"
        "回答应简洁、准确。若用户需要**深度检索、来源对比、长篇调研**，"
        "请通过 task 工具委托给子代理 `research`，不要凭空编造网页内容。"
    )

    return create_deep_agent(
        model=llm,
        system_prompt=system_prompt,
        subagents=[research_subagent],
        checkpointer=checkpointer,
    )
