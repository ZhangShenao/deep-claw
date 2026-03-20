from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

from app.agent.build import build_deep_agent
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.history import router as history_router
from app.config import get_settings
from app.db.session import init_db
from langgraph.checkpoint.mongodb import MongoDBSaver


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_db()

    client = MongoClient(settings.mongodb_uri)
    checkpointer = MongoDBSaver(client, db_name=settings.mongodb_db_name)
    graph = build_deep_agent(settings, checkpointer)

    app.state.mongo_client = client
    app.state.graph = graph

    yield

    client.close()


def create_app() -> FastAPI:
    settings = get_settings()
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if not origins:
        origins = ["*"]

    app = FastAPI(title="Deep-Claw API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(conversations_router)
    app.include_router(history_router)
    app.include_router(chat_router)
    return app


app = create_app()
