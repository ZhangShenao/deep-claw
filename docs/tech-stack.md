# 技术选型

## 约束（来自产品/技术需求）

| 类别 | 选型 | 说明 |
|------|------|------|
| 语言 | Python 3.12 | 后端 |
| 包管理 | uv | `uv sync` / `uv run` |
| API | FastAPI | REST + SSE |
| Agent 框架 | deepagents ≥ 0.4 | `create_deep_agent`，Sub-Agent |
| 运行时 | langgraph ≥ 1.0 | 编译图、流式、checkpoint |
| LLM | langchain-openai `ChatOpenAI` | `base_url` + `api_key` 对接智谱 GLM 兼容接口 |
| 检索 | Tavily API | 深度调研子代理工具 |
| 可观测 | LangSmith | `LANGCHAIN_TRACING_V2` 等 |
| 对话状态 | MongoDB | `langgraph-checkpoint-mongodb` |
| 业务库 | PostgreSQL | SQLAlchemy 2.x + async |
| 前端 | Next.js（App Router） | React 19 / Next 15 随脚手架 |
| 部署 | Docker Compose | 一键编排 |

## Python 依赖（概要）

- `fastapi`, `uvicorn[standard]`
- `deepagents`, `langgraph`, `langchain-openai`, `langchain-core`
- `langgraph-checkpoint-mongodb`
- `langsmith`（随 langchain 生态）
- `tavily-python`（或 `langchain-community` Tavily 工具，实现时择一并保持最小）
- `sqlalchemy[asyncio]`, `asyncpg`
- `pydantic-settings`

## 前端依赖（概要）

- `next`, `react`, `react-dom`, `typescript`

## LLM（智谱 GLM）

通过环境变量配置 `OPENAI_BASE_URL`（如智谱 OpenAI 兼容地址）、`OPENAI_API_KEY`、`OPENAI_MODEL`。具体模型名以智谱文档为准，不在仓库写死业务模型名。
