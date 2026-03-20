# 数据模型

## PostgreSQL（业务）

一期单用户，仅会话元数据，便于列表与展示。

**表 `conversations`**

| 列 | 类型 | 说明 |
|----|------|------|
| `id` | UUID PK | 与 LangGraph `thread_id` 一致 |
| `title` | TEXT | 可由首条用户消息截断生成 |
| `created_at` | TIMESTAMPTZ | 默认 now |
| `updated_at` | TIMESTAMPTZ | 每次消息更新 |

不在 PG 存完整消息正文；**权威对话状态在 MongoDB checkpoint**。

## MongoDB（Checkpoint）

- 使用 `langgraph-checkpoint-mongodb` 默认集合（或配置前缀）。
- 存储 LangGraph 状态与历史，支持中断恢复与多轮。

## 一致性

- 创建会话：先写 PG 一行，再使用该 `id` 作为 `thread_id` 调用 Agent。
- 删除会话（若实现）：删除 PG 行；可选异步清理 Mongo checkpoint（一期可仅删 PG，Mongo 留 TTL 或手动清理）。
