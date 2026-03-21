from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver

from deepagents import create_deep_agent

from app.agent.email_digest_agent import EMAIL_DIGEST_SYSTEM_PROMPT
from app.agent.tools import (
    build_current_datetime_tool,
    build_internet_search,
    build_list_connected_email_accounts_tool,
    build_list_email_digests_tool,
    build_run_email_check_tool,
)
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
    current_datetime = build_current_datetime_tool()
    list_connected_email_accounts = build_list_connected_email_accounts_tool()
    run_email_check = build_run_email_check_tool()
    list_email_digests = build_list_email_digests_tool()

    research_subagent = {
        "name": "research",
        "description": (
            "用于深度网络调研：多关键词检索、对比来源、输出结构化摘要与要点。"
            "当用户需要最新网页信息、行业数据、新闻或引用来源时使用。"
            "凡涉及最新、当前、今天、本周、本月等时效性判断，先调用 get_current_datetime。"
        ),
        "system_prompt": (
            "你在开始任何时效性调研前，必须先调用 get_current_datetime 获取当前日期与时间。"
            "你是深度调研助手。仅使用提供的 internet_search 工具获取网络信息；"
            "综合多轮检索结果，用中文输出：摘要、分点要点、并注明信息局限。"
            "不要编造 URL 或引用。"
        ),
        "tools": [current_datetime, internet_search],
    }

    email_subagent = {
        "name": "email",
        "description": (
            "用于检查已接入邮箱、总结最新邮件、查看已有邮件摘要，并给出下一步行动建议。"
            "当用户明确要求检查邮件、总结收件箱、查看未读重点时使用。"
        ),
        "system_prompt": EMAIL_DIGEST_SYSTEM_PROMPT
        + " 当用户要检查邮件时，先查看已接入邮箱；如存在多个邮箱，优先选择最近唯一的或请主代理澄清。"
        + " 需要执行检查时调用 run_email_check。"
        + " 不要执行发信、删除、归档或标记已读。",
        "tools": [list_connected_email_accounts, run_email_check, list_email_digests],
    }

    system_prompt = (
        "你是 Deep-Claw 个人助理，帮助用户完成日常对话与任务编排。"
        "回答应简洁、准确。若用户需要**深度检索、来源对比、长篇调研**，"
        "请通过 task 工具委托给子代理 `research`，不要凭空编造网页内容。"
        "若用户明确要求检查邮件、总结最新邮件、查看收件箱重点，"
        "请通过 task 工具委托给子代理 `email`。"
        "只要问题涉及最新、当前、今天、近期、截至目前等时间敏感信息，"
        "必须先调用 get_current_datetime，再继续回答或委托调研。"
    )

    return create_deep_agent(
        model=llm,
        system_prompt=system_prompt,
        tools=[current_datetime],
        subagents=[research_subagent, email_subagent],
        checkpointer=checkpointer,
    )
