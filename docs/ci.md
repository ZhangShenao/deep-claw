# CI/CD

## GitHub Actions

| Workflow | 触发 | 内容 |
|----------|------|------|
| [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | `push` / `pull_request` 至 `main` 或 `master` | **backend**：`uv sync --group dev` + `pytest`（Job 内 PostgreSQL + MongoDB **services**）；**frontend**：`npm ci`、`npm run lint`、`npm run build` |
| [`.github/workflows/docker-publish.yml`](../.github/workflows/docker-publish.yml) | 打 `v*` **tag** 或 **手动** `workflow_dispatch` | 构建并推送 `backend` / `frontend` 镜像至 **GHCR**：`ghcr.io/<owner>/<repo>/backend` 与 `.../frontend` |

## 本地运行集成测试

需本机可访问的 PostgreSQL 与 MongoDB（与 [docker-compose.yml](../docker-compose.yml) 端口一致）：

```bash
docker compose up -d postgres mongo
cd backend
uv sync --group dev
uv run pytest
```

环境变量未设置时，`tests/conftest.py` 使用与 CI 相同的默认连接串（`localhost:5432`、`localhost:27017`）。

## 生产部署（占位）

镜像发布后可自行在服务器上 `docker compose pull`（需将 `image:` 改为 GHCR 地址）或通过 SSH、K8s 等拉取部署；具体编排不在本仓库强制约定。

## 仓库设置提示

- 使用 GHCR：仓库 **Settings → Actions → General** 中确认 `GITHUB_TOKEN` 对 Packages 的写权限（视组织策略而定）。
- 可选：为 `main` 分支启用 **Branch protection**，要求 **CI** workflow 通过后再合并。
