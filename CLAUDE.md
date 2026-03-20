# Deep-Claw — 协作说明

## 项目与一期范围

基于 **LangChain DeepAgents / LangGraph** 的轻量化个人助理：**仅 Web 聊天**；主 Agent 对话 + **深度调研 Sub-Agent（Tavily）**；**单用户、无登录**。业务数据在 PostgreSQL，对话 checkpoint 在 MongoDB。

## 文档入口

- 架构与流程：[docs/architecture.md](docs/architecture.md)
- Agent 与子代理：[docs/agent-design.md](docs/agent-design.md)
- API 与 SSE：[docs/api-and-streaming.md](docs/api-and-streaming.md)
- 部署：[docs/deployment.md](docs/deployment.md)
- 索引：[docs/README.md](docs/README.md)

## 开发纪律（必读）

在编写或修改调用 **LangChain、LangGraph、DeepAgents、LangSmith、MongoDB Checkpoint、Tavily、FastAPI、Next.js** 的代码前：

1. 使用 **Context7 MCP**（`user-context7` → `query-docs`）查询**当前版本**的官方 API 与示例。
2. 若未知 library id，先通过 Context7 的 **Resolve Library ID** 流程得到 `/org/project` 或带版本的形式，再发起 `query-docs`。
3. 长文设计以 `docs/` 为准；本文件保持精简。

## 仓库布局

- `backend/` — FastAPI + Agent
- `frontend/` — Next.js
- `docker-compose.yml` — 编排
- `scripts/deploy.sh` — 一键启动
