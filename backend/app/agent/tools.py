"""Tavily-backed search tool for the research sub-agent."""

from typing import Any, Literal

from langchain_core.tools import tool
from tavily import TavilyClient

from app.config import Settings


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
