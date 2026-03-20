# Agent 设计

## 主 Agent

- 使用 `deepagents.create_deep_agent`（见官方文档）。
- **模型**：`ChatOpenAI`，从配置读取 `base_url`、`api_key`、`model`。
- **系统提示（概要）**：你是 Deep-Claw 个人助理；友好完成日常对话；当用户需要**深度检索、对比来源、长篇调研**时，使用 **task 工具**将任务交给名为 `research` 的子代理，不要自己编造引用。

## Sub-Agent：深度调研（`research`）

- **name**：`research`（实现中与 DeepAgents subagents 配置一致）。
- **system_prompt**：强调多步检索、引用要点、结构化输出（摘要 + 要点列表）；仅使用提供的 Tavily 工具获取网络信息。
- **tools**：Tavily 搜索工具（`tavily-python` 封装为 LangChain `StructuredTool` 或官方集成）。

## Skills 边界（一期）

DeepAgents 的「skills」若指官方 **skill 文件/可加载技能包**：一期不单独引入技能文件系统；**主 Agent + 子代理 + 工具** 已覆盖「深度调研」场景。二期可扩展为独立 skill 目录或 MCP。

## 工具与安全（一期收敛）

DeepAgents 默认可能包含 **文件、Shell** 等能力。生产级轻量化部署下一期策略：

- **禁用或移除** 主机 `execute`、真实文件系统写操作（若框架默认注入），仅保留：**对话、规划类（如 write_todos，若需）、task/subagent、Tavily**。
- 具体以 `create_deep_agent` 当前参数为准（如 `tools=` 覆盖、`middleware` 等），实现时代码显式列出允许的工具集。

## Checkpoint

- 使用 **MongoDB** Async checkpointer，与 `thread_id` 绑定。
- 会话 ID 与 `thread_id` 一致（UUID），便于前后端对齐。
