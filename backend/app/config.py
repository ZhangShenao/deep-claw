from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/deep_claw"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "deep_claw"

    openai_api_key: str = ""
    openai_base_url: str | None = None
    openai_model: str = "glm-4-plus"

    tavily_api_key: str = ""

    cors_origins: str = "*"

    # 与 deepagents 默认 1000 对齐；传入 astream_events 的 config 需显式带上，否则会回落到 LangGraph 默认 25
    langgraph_recursion_limit: int = 1000


@lru_cache
def get_settings() -> Settings:
    return Settings()
