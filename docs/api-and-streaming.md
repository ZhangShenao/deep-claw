# API 与流式协议

## 基础 URL

- 本地开发：`http://localhost:8000`
- 前端通过 `NEXT_PUBLIC_API_BASE` 配置。

## REST

### `GET /health`

返回 `{"status": "ok"}`。

### `GET /api/conversations`

返回会话列表：`[{ "id", "title", "created_at", "updated_at" }]`。

### `POST /api/conversations`

Body：`{ "title"?: string }`（可选，默认「新对话」）。

返回：`{ "id", "title", "created_at", "updated_at" }`。

### `DELETE /api/conversations/{id}`

删除会话元数据（可选实现）。

### `GET /api/conversations/{id}/messages`

从 LangGraph checkpoint 恢复该线程的 `messages`（供前端切换会话时展示历史）。不含 tool 消息的详细内容。

### `POST /api/chat/stream`

- **Content-Type**：`application/json`
- Body：
  - `thread_id`：UUID 字符串
  - `message`：用户最新一条消息文本

**Response**：`text/event-stream`（SSE）

每条事件一行：`data: <JSON>\n\n`

## SSE 事件 JSON Schema（逻辑约定）

| `type` | 说明 | 附加字段 |
|--------|------|----------|
| `token` | 模型增量文本 | `content`: string |
| `tool_start` | 工具开始 | `name`, `input`（可序列化摘要） |
| `tool_end` | 工具结束 | `name`, `output`（摘要） |
| `subagent` | 子代理生命周期提示 | `phase`: `start` \| `end`, `name` |
| `message` | 完整消息块（可选） | `role`, `content` |
| `done` | 流结束 | `thread_id` |
| `error` | 错误 | `message` |

实现基于 LangGraph `astream_events`（或等价 API），将 `on_chat_model_stream`、`on_tool_start` 等映射到上表。

## CORS

后端对前端 origin 开放（开发 `*` 或可配置）。
