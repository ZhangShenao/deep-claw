#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f "$ROOT/.env" ]]; then
  echo "提示: 未找到 .env，可从 .env.example 复制并填写密钥。"
fi

docker compose up -d --build

echo ""
echo "健康检查: curl -s http://localhost:8000/health"
echo "后端 API: http://localhost:8000/docs"
echo "前端页面: http://localhost:3000"
