"""Tavily-backed search tool for the research sub-agent."""

from datetime import datetime, timezone
from typing import Any, Literal

from langchain_core.tools import tool
from tavily import TavilyClient

from app.config import Settings


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
