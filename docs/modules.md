# 模块划分

## 仓库结构（目标）

```
deep-claw/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 应用入口
│   │   ├── config.py            # 环境配置
│   │   ├── api/                 # 路由：health, conversations, history, chat
│   │   ├── agent/               # Deep Agent 构建、工具、子代理
│   │   └── db/                  # PostgreSQL 模型与会话仓库
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── app/                     # Next.js App Router
│   ├── components/
│   └── Dockerfile
├── scripts/
│   └── deploy.sh
├── docker-compose.yml
└── docs/
```

## 后端模块

| 模块 | 职责 |
|------|------|
| `config` | `pydantic-settings`：数据库 URI、Mongo、OpenAI、Tavily、LangSmith |
| `db` | SQLAlchemy models：`Conversation`；异步 session；建表 |
| `agent/graph` | `build_agent()`：`create_deep_agent`、checkpointer、`subagents`、Tavily 工具 |
| `api/conversations` | 列出/创建/可选删除会话 |
| `api/chat` | SSE：输入消息 + `thread_id`，流式输出 |

## 前端模块

| 模块 | 职责 |
|------|------|
| `app/page` 或 `app/chat` | 布局：侧栏会话 + 主聊天 |
| `components/Chat` | 输入框、消息列表、SSE `EventSource` |
| `lib/sse` | 解析 `data: {...}` 行，更新 UI 状态 |

## 依赖方向

- `api` → `agent`、`db`
- `agent` → `config`、不依赖 `api`
