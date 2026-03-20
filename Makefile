.PHONY: deploy backend dev frontend-dev

deploy:
	./scripts/deploy.sh

backend:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev:
	cd frontend && npm run dev
