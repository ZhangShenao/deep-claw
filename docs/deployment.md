# 部署

## Docker Compose 服务

| 服务 | 镜像/构建 | 端口 | 说明 |
|------|-----------|------|------|
| `postgres` | `postgres:16-alpine` | 5432 | 业务库 |
| `mongo` | `mongo:7` | 27017 | Checkpoint |
| `backend` | `./backend` | 8000 | FastAPI |
| `frontend` | `./frontend` | 3000 | Next.js |

## 环境变量（`.env` 示例）

见根目录 `README.md` 环境变量表。Compose 中通过 `env_file` 或 `environment` 注入。

## 数据卷

- `postgres_data`、`mongo_data` 命名卷持久化。

## 一键脚本

- `scripts/deploy.sh`：`docker compose up -d --build`
- 健康检查：`curl http://localhost:8000/health`

## 首次启动

- 后端启动时自动 `create_all` 创建 PG 表（一期）。

## CI/CD

持续集成与镜像发布说明见 [ci.md](./ci.md)（GitHub Actions、`pytest` 本地命令、GHCR 镜像路径）。
