"""Tavily-backed search tool for the research sub-agent."""

from datetime import datetime, timezone
import uuid
from typing import Any, Literal

from langchain_core.tools import tool
from tavily import TavilyClient

from app.config import Settings
from app.db import email_accounts as email_accounts_repo
from app.db import email_messages as email_messages_repo
from app.db.session import get_session
from app.email.service import run_manual_email_check


def build_current_datetime_tool():
    @tool("get_current_datetime")
    def get_current_datetime() -> str:
        """Get the current local date/time and UTC date/time. Use this before answering any latest/current/today time-sensitive question."""

        now_utc = datetime.now(timezone.utc)
        now_local = now_utc.astimezone()
        return (
            f"Local time: {now_local.isoformat()} (timezone: {now_local.tzname() or 'local'}); "
            f"Local date: {now_local.date().isoformat()}; "
            f"UTC time: {now_utc.isoformat()}"
        )

    return get_current_datetime


def build_internet_search(settings: Settings):
    if not settings.tavily_api_key:
        @tool
        def internet_search_disabled(query: str) -> str:
            """Search the public internet. Unavailable: TAVILY_API_KEY is not set."""
            del query
            return "Tavily API key is not configured. Set TAVILY_API_KEY to enable web search."

        return internet_search_disabled

    client = TavilyClient(api_key=settings.tavily_api_key)

    @tool
    def internet_search(
        query: str,
        max_results: int = 5,
        topic: Literal["general", "news", "finance"] = "general",
        include_raw_content: bool = False,
    ) -> dict[str, Any]:
        """Run a web search for deep research. Returns Tavily JSON (results and snippets)."""
        return client.search(
            query,
            max_results=max_results,
            include_raw_content=include_raw_content,
            topic=topic,
        )

    return internet_search


def build_list_connected_email_accounts_tool():
    @tool
    async def list_connected_email_accounts() -> list[dict[str, Any]]:
        """List connected email accounts available for email checks."""
        async with get_session() as session:
            rows = await email_accounts_repo.list_accounts(session)

        return [
            {
                "account_id": str(row.id),
                "email_address": row.email_address,
                "provider_label": row.provider_label,
                "poll_interval_minutes": row.poll_interval_minutes,
                "enabled": row.enabled,
            }
            for row in rows
        ]

    return list_connected_email_accounts


def build_run_email_check_tool():
    @tool
    async def run_email_check(account_id: str) -> dict[str, Any]:
        """Run a manual email check for a connected account and return the latest digest summary."""
        async with get_session() as session:
            result = await run_manual_email_check(session, uuid.UUID(account_id))

        return {
            "digest_id": str(result.digest_id),
            "account_id": str(result.account_id),
            "trigger_source": result.trigger_source,
            "new_message_count": result.new_message_count,
            "summary": result.summary,
        }

    return run_email_check


def build_list_email_digests_tool():
    @tool
    async def list_email_digests(account_id: str | None = None) -> list[dict[str, Any]]:
        """List stored email digests, optionally filtered by account id."""
        async with get_session() as session:
            rows = await email_messages_repo.list_digests(session)

        if account_id:
            rows = [row for row in rows if str(row.account_id) == account_id]

        return [
            {
                "digest_id": str(row.id),
                "account_id": str(row.account_id),
                "trigger_source": row.trigger_source,
                "summary": row.summary,
                "priority": row.priority,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    return list_email_digests
