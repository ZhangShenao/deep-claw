# 可观测性（LangSmith）

## 环境变量

| 变量 | 说明 |
|------|------|
| `LANGCHAIN_TRACING_V2` | 设为 `true` 启用追踪 |
| `LANGCHAIN_API_KEY` | LangSmith API Key |
| `LANGCHAIN_PROJECT` | 项目名称（可选） |
| `LANGCHAIN_ENDPOINT` | 默认官方，私有化时覆盖 |

## 行为

- 启用后，LangChain / LangGraph 调用链上报 LangSmith，便于查看工具调用、子图与延迟。
- 未配置 Key 时本地开发可关闭追踪，不影响服务启动。

## 隐私

- 勿在日志中打印完整用户密钥；生产环境限制 LangSmith 采样或脱敏（按组织策略）。
