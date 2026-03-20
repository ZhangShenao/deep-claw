"""HTTP API integration tests (requires PostgreSQL + MongoDB)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(async_client: AsyncClient) -> None:
    r = await async_client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_conversations_crud_and_messages(async_client: AsyncClient) -> None:
    r = await async_client.post("/api/conversations", json={})
    assert r.status_code == 200
    body = r.json()
    assert "id" in body
    assert "title" in body
    cid = body["id"]

    r = await async_client.get("/api/conversations")
    assert r.status_code == 200
    assert any(c["id"] == cid for c in r.json())

    r = await async_client.get(f"/api/conversations/{cid}/messages")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    r = await async_client.delete(f"/api/conversations/{cid}")
    assert r.status_code == 204

    r = await async_client.get("/api/conversations")
    assert r.status_code == 200
    assert not any(c["id"] == cid for c in r.json())
