# Deep-Claw

基于 LangChain **DeepAgents** / **LangGraph** 的轻量化个人助理：Web 聊天、主 Agent 日常对话、**深度调研 Sub-Agent**（Tavily 网络搜索）。一期单用户、无登录。

完整技术说明见 **[docs/README.md](docs/README.md)**。协作规范见 **[CLAUDE.md](CLAUDE.md)**。CI/CD 与集成测试见 **[docs/ci.md](docs/ci.md)**（推送至 GitHub 后在 **Actions** 中查看运行结果；可在仓库 **Settings → General** 启用状态徽章并嵌入 README）。

## 功能

- 会话列表与多轮对话（checkpoint 持久化）
- 流式输出（SSE）：文本增量、工具步骤、子代理提示
- LangSmith 可观测（可选）
- Docker Compose 一键部署

## 仓库结构

```
backend/       # FastAPI，Python 3.12 + uv
frontend/      # Next.js App Router
docs/          # 技术方案与 API 约定
scripts/       # deploy.sh
docker-compose.yml
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | PostgreSQL，如 `postgresql+asyncpg://user:pass@host:5432/db` |
| `MONGODB_URI` | MongoDB，如 `mongodb://host:27017` |
| `MONGODB_DB_NAME` | Checkpoint 数据库名（默认 `deep_claw`） |
| `OPENAI_API_KEY` | 智谱等 OpenAI 兼容 Key |
| `OPENAI_BASE_URL` | 如智谱 OpenAI 兼容 Base URL |
| `OPENAI_MODEL` | 模型名（如 GLM 系列） |
| `TAVILY_API_KEY` | Tavily API Key |
| `LANGCHAIN_TRACING_V2` | `true` 启用 LangSmith |
| `LANGCHAIN_API_KEY` | LangSmith API Key |
| `LANGCHAIN_PROJECT` | LangSmith 项目名（可选） |
| `CORS_ORIGINS` | 逗号分隔允许来源，默认 `*` |
| `NEXT_PUBLIC_API_BASE` | 前端访问后端 API 的根 URL |

## 本地开发

### 后端

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

需本机或使用 Compose 启动 PostgreSQL 与 MongoDB，并设置环境变量。

**集成测试**（需 PG + Mongo 已启动）：

```bash
cd backend
uv sync --group dev
uv run pytest
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

设置 `NEXT_PUBLIC_API_BASE=http://localhost:8000`。

## Docker Compose

```bash
cp .env.example .env   # 编辑密钥与模型
./scripts/deploy.sh
# 或: make deploy
```

- 后端：<http://localhost:8000/health> · OpenAPI：<http://localhost:8000/docs>
- 前端：<http://localhost:3000>

`docker compose` 会读取当前目录下的 `.env`（可将 `.env.example` 复制为 `.env` 后填写 `OPENAI_API_KEY`、`TAVILY_API_KEY` 等）。

## License

MIT（与依赖库许可证分别遵循各项目）
