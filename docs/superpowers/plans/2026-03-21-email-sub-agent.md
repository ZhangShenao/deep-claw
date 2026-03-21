# Email Sub-Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build phase-one email integration for Deep-Claw with IMAP account connection, scheduled email digest generation, in-app SSE notifications, and manual email checks through a new Email Sub-Agent.

**Architecture:** Persist all email business state in PostgreSQL, keep MongoDB reserved for chat checkpoints, and run automatic email polling in a dedicated worker process. Reuse one email analysis service for both scheduled worker runs and chat-triggered manual checks, while keeping scheduled runs isolated from chat thread history.

**Tech Stack:** FastAPI, SQLAlchemy async, DeepAgents, LangGraph, ChatOpenAI-compatible LLM, IMAP over TLS, Next.js App Router, React client components, SSE

---

## File Structure

### Backend files to modify

- `backend/app/config.py`
  Adds email feature settings such as credential encryption key, worker polling cadence, digest batch limits, and optional default IMAP timeouts.
- `backend/app/main.py`
  Registers new email and notification routers in the FastAPI app.
- `backend/app/api/schemas.py`
  Adds request/response models for email accounts, digests, and notifications.
- `backend/app/agent/build.py`
  Registers the new `email` subagent and updates the main agent prompt to delegate explicit email-check requests.
- `backend/app/agent/tools.py`
  Keeps Tavily search and gains helper functions or tool builders reused by the email subagent.
- `backend/app/db/models.py`
  Adds `EmailAccount`, `EmailSyncState`, `EmailMessage`, `EmailDigest`, and `Notification` tables.
- `backend/app/db/session.py`
  Ensures new models participate in `create_all`.
- `docker-compose.yml`
  Adds an `email-worker` service and required environment variables.

### Backend files to create

- `backend/app/api/email.py`
  Email account CRUD, digest list/detail, and check-now endpoints.
- `backend/app/api/notifications.py`
  Notification list, mark-read, and SSE stream endpoints.
- `backend/app/db/email_accounts.py`
  Repository helpers for account CRUD and sync-state management.
- `backend/app/db/email_messages.py`
  Repository helpers for normalized email storage and digest queries.
- `backend/app/db/notifications.py`
  Repository helpers for notification persistence and read state.
- `backend/app/email/crypto.py`
  Encrypt/decrypt mailbox credentials using an app-level symmetric key.
- `backend/app/email/client.py`
  IMAP connection helpers and fetch primitives.
- `backend/app/email/parser.py`
  MIME parsing, quote trimming, snippet extraction, and message normalization.
- `backend/app/email/service.py`
  Shared orchestration for manual and scheduled email fetch + digest generation.
- `backend/app/email/worker.py`
  Worker loop that claims due accounts and runs scheduled checks.
- `backend/app/email/__init__.py`
  Package marker.

### Frontend files to modify

- `frontend/lib/api.ts`
  Adds email account, digest, notification, and SSE helper functions/types.
- `frontend/components/ChatApp.tsx`
  Subscribes to notification SSE, exposes digest/notification UI regions, and offers a lightweight email-management experience.

### Frontend files to create

- `frontend/components/EmailAccountsPanel.tsx`
  Mailbox settings UI and manual check controls.
- `frontend/components/EmailDigestList.tsx`
  Digest list and selected-digest detail rendering.
- `frontend/components/NotificationTray.tsx`
  In-app notifications display and mark-read interactions.

### Tests to create or modify

- `backend/tests/conftest.py`
  Adds test env vars for encryption and worker defaults.
- `backend/tests/test_integration_api.py`
  Keeps chat/conversation coverage and gains router registration regression checks.
- `backend/tests/test_email_api.py`
  Covers account CRUD, digest retrieval, and notification APIs.
- `backend/tests/test_email_service.py`
  Covers IMAP normalization, incremental sync, digest generation, and no-chat-checkpoint scheduled runs.

## Task 1: Database Schema and Configuration

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/db/models.py`
- Modify: `backend/app/db/session.py`
- Modify: `backend/tests/conftest.py`
- Test: `backend/tests/test_email_api.py`

- [ ] **Step 1: Write the failing schema/API smoke test**

```python
async def test_list_email_accounts_initially_empty(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/email/accounts")
    assert response.status_code == 200
    assert response.json() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_email_api.py::test_list_email_accounts_initially_empty -v`
Expected: FAIL with `404 Not Found` or missing route/model errors.

- [ ] **Step 3: Add settings and SQLAlchemy models**

```python
class Settings(BaseSettings):
    email_credential_key: str = "test-email-key"
    email_worker_poll_seconds: int = 15
    email_digest_max_messages: int = 20
```

```python
class EmailAccount(Base):
    __tablename__ = "email_accounts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_address: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
```

- [ ] **Step 4: Run the targeted test again**

Run: `uv run pytest backend/tests/test_email_api.py::test_list_email_accounts_initially_empty -v`
Expected: still FAIL, but now on missing router/repository behavior instead of missing schema.

- [ ] **Step 5: Commit the schema/config slice**

```bash
git add backend/app/config.py backend/app/db/models.py backend/app/db/session.py backend/tests/conftest.py
git commit -m "feat: add email data models"
```

## Task 2: Email Repositories and FastAPI APIs

**Files:**
- Create: `backend/app/db/email_accounts.py`
- Create: `backend/app/db/email_messages.py`
- Create: `backend/app/db/notifications.py`
- Create: `backend/app/api/email.py`
- Create: `backend/app/api/notifications.py`
- Modify: `backend/app/api/schemas.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_email_api.py`

- [ ] **Step 1: Write failing API tests for account create/list and notification list**

```python
async def test_create_email_account(async_client: AsyncClient) -> None:
    payload = {
        "email_address": "user@example.com",
        "provider_label": "Example",
        "imap_host": "imap.example.com",
        "imap_port": 993,
        "auth_type": "app_password",
        "credential": "secret",
        "poll_interval_minutes": 15,
    }
    response = await async_client.post("/api/email/accounts", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["email_address"] == "user@example.com"
    assert body["enabled"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/test_email_api.py -v`
Expected: FAIL with missing routes or response schema mismatches.

- [ ] **Step 3: Implement repositories, schemas, and routers**

```python
@router.get("/api/email/accounts", response_model=list[EmailAccountOut])
async def list_email_accounts(session: AsyncSession = Depends(get_db)) -> list[EmailAccountOut]:
    return await email_accounts_repo.list_accounts(session)
```

```python
@router.get("/api/notifications", response_model=list[NotificationOut])
async def list_notifications(session: AsyncSession = Depends(get_db)) -> list[NotificationOut]:
    return await notifications_repo.list_notifications(session)
```

- [ ] **Step 4: Run API tests to verify they pass**

Run: `uv run pytest backend/tests/test_email_api.py -v`
Expected: PASS for account CRUD, digest retrieval stubs, and notification endpoints.

- [ ] **Step 5: Commit the API slice**

```bash
git add backend/app/api backend/app/db backend/tests/test_email_api.py backend/app/main.py
git commit -m "feat: add email account and notification APIs"
```

## Task 3: IMAP Client, Credential Encryption, and Normalization

**Files:**
- Create: `backend/app/email/crypto.py`
- Create: `backend/app/email/client.py`
- Create: `backend/app/email/parser.py`
- Create: `backend/app/email/__init__.py`
- Test: `backend/tests/test_email_service.py`

- [ ] **Step 1: Write failing unit tests for encryption and normalized message parsing**

```python
def test_encrypt_round_trip(settings: Settings) -> None:
    token = encrypt_secret("app-password", settings)
    assert decrypt_secret(token, settings) == "app-password"
```

```python
def test_normalize_email_message_trims_quotes() -> None:
    normalized = normalize_email_message(raw_email_bytes)
    assert "On Tue," not in normalized.body_text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/test_email_service.py -v`
Expected: FAIL with missing crypto/parser functions.

- [ ] **Step 3: Implement minimal crypto and parsing modules**

```python
def encrypt_secret(value: str, settings: Settings) -> str:
    signer = _build_fernet(settings.email_credential_key)
    return signer.encrypt(value.encode("utf-8")).decode("utf-8")
```

```python
def normalize_email_message(raw_bytes: bytes) -> NormalizedEmail:
    message = email.message_from_bytes(raw_bytes)
    body_text = trim_quoted_text(extract_plain_text(message))
    return NormalizedEmail(subject=message.get("Subject", ""), body_text=body_text)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest backend/tests/test_email_service.py -v`
Expected: PASS for crypto round-trip and normalization behavior.

- [ ] **Step 5: Commit the infrastructure slice**

```bash
git add backend/app/email backend/tests/test_email_service.py backend/app/config.py backend/pyproject.toml
git commit -m "feat: add email parsing and credential encryption"
```

## Task 4: Shared Email Service and Scheduled Worker

**Files:**
- Create: `backend/app/email/service.py`
- Create: `backend/app/email/worker.py`
- Modify: `backend/app/db/email_accounts.py`
- Modify: `backend/app/db/email_messages.py`
- Modify: `docker-compose.yml`
- Test: `backend/tests/test_email_service.py`

- [ ] **Step 1: Write failing service tests for incremental sync and digest persistence**

```python
async def test_sync_new_messages_creates_digest(session: AsyncSession) -> None:
    result = await run_email_check(account_id, trigger_source="scheduled")
    assert result.digest_id is not None
    assert result.new_message_count == 2
```

```python
async def test_scheduled_run_does_not_require_chat_thread(session: AsyncSession) -> None:
    result = await run_email_check(account_id, trigger_source="scheduled")
    assert result.thread_id is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/test_email_service.py -v`
Expected: FAIL with missing service/worker orchestration.

- [ ] **Step 3: Implement shared orchestration and worker loop**

```python
async def run_email_check(account_id: uuid.UUID, trigger_source: str) -> EmailCheckResult:
    account = await email_accounts_repo.get_account(session, account_id, for_update=True)
    fetched = await imap_client.fetch_since_uid(account, sync_state.last_seen_uid)
    stored = await email_messages_repo.store_messages(session, account.id, fetched)
    digest = await build_email_digest(stored, trigger_source=trigger_source)
    return EmailCheckResult(digest_id=digest.id, new_message_count=len(stored))
```

```python
async def worker_loop() -> None:
    while True:
        claimed = await claim_due_accounts(limit=5)
        for account_id in claimed:
            await run_email_check(account_id, trigger_source="scheduled")
        await asyncio.sleep(settings.email_worker_poll_seconds)
```

- [ ] **Step 4: Run service tests to verify they pass**

Run: `uv run pytest backend/tests/test_email_service.py -v`
Expected: PASS for incremental sync, digest creation, and scheduled isolation behavior.

- [ ] **Step 5: Commit the worker slice**

```bash
git add backend/app/email/service.py backend/app/email/worker.py backend/app/db docker-compose.yml backend/tests/test_email_service.py
git commit -m "feat: add scheduled email worker"
```

## Task 5: Email Sub-Agent and Manual Chat-Triggered Check

**Files:**
- Modify: `backend/app/agent/build.py`
- Modify: `backend/app/agent/tools.py`
- Modify: `backend/app/api/email.py`
- Modify: `backend/tests/test_email_service.py`
- Modify: `backend/tests/test_integration_api.py`

- [ ] **Step 1: Write failing tests for manual email-check behavior**

```python
async def test_check_now_creates_digest(async_client: AsyncClient) -> None:
    response = await async_client.post(f"/api/email/accounts/{account_id}/check-now")
    assert response.status_code == 200
    assert response.json()["trigger_source"] == "manual"
```

```python
async def test_main_agent_registers_email_subagent() -> None:
    graph = build_deep_agent(settings, checkpointer)
    assert graph is not None
```

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `uv run pytest backend/tests/test_email_service.py backend/tests/test_integration_api.py -v`
Expected: FAIL with missing manual-check flow or missing email subagent wiring.

- [ ] **Step 3: Register email subagent and wire manual checks**

```python
email_subagent = {
    "name": "email",
    "description": "用于检查已接入邮箱、总结最新邮件并给出行动建议。",
    "system_prompt": "你是只读邮件助手。只基于提供的邮件内容总结，不要编造，也不要执行发信或删除。",
    "tools": [list_connected_email_accounts, fetch_recent_email_batch, get_email_message_detail],
}
```

- [ ] **Step 4: Run the relevant backend tests**

Run: `uv run pytest backend/tests/test_email_service.py backend/tests/test_integration_api.py -v`
Expected: PASS for manual check-now flow and agent wiring regressions.

- [ ] **Step 5: Commit the agent slice**

```bash
git add backend/app/agent backend/app/api/email.py backend/tests/test_email_service.py backend/tests/test_integration_api.py
git commit -m "feat: add email subagent integration"
```

## Task 6: Notification SSE and Frontend Email Experience

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/components/ChatApp.tsx`
- Create: `frontend/components/EmailAccountsPanel.tsx`
- Create: `frontend/components/EmailDigestList.tsx`
- Create: `frontend/components/NotificationTray.tsx`
- Modify: `backend/app/api/notifications.py`

- [ ] **Step 1: Write the failing frontend/data-flow checks**

```tsx
export type NotificationEvent =
  | { type: "notification"; id: string; title: string; body: string; payload: { digest_id: string } }
  | { type: "heartbeat" }
  | { type: "error"; message: string }
```

Manual verification target:
- opening the app shows mailbox settings
- new notifications appear without refreshing
- clicking a notification reveals the matching digest

- [ ] **Step 2: Run lint/build to establish the current baseline**

Run: `npm run lint`
Run: `npm run build`
Expected: PASS before edits.

- [ ] **Step 3: Implement API helpers, SSE subscription, and UI panels**

```tsx
useEffect(() => {
  const controller = new AbortController()
  streamNotifications((event) => setNotifications((prev) => [event, ...prev]), { signal: controller.signal })
  return () => controller.abort()
}, [])
```

- [ ] **Step 4: Run lint/build after the frontend changes**

Run: `npm run lint`
Run: `npm run build`
Expected: PASS with the new email and notification UI.

- [ ] **Step 5: Commit the frontend slice**

```bash
git add frontend/lib/api.ts frontend/components
git commit -m "feat: add email notifications ui"
```

## Task 7: Full Verification and Documentation Alignment

**Files:**
- Modify: `docs/data-model.md`
- Modify: `docs/api-and-streaming.md`
- Modify: `docs/agent-design.md`
- Test: `backend/tests/test_email_api.py`
- Test: `backend/tests/test_email_service.py`

- [ ] **Step 1: Update docs to match implemented behavior**

```md
- PostgreSQL stores email accounts, digests, and notifications.
- MongoDB remains limited to chat checkpoints.
- `/api/notifications/stream` delivers in-app SSE notifications.
```

- [ ] **Step 2: Run the complete backend test suite**

Run: `uv run pytest`
Expected: PASS for conversations, email APIs, service logic, and agent integration.

- [ ] **Step 3: Run the complete frontend verification commands**

Run: `npm run lint`
Run: `npm run build`
Expected: PASS.

- [ ] **Step 4: Review `git diff` for accidental scope creep**

Run: `git diff --stat HEAD~1..HEAD`
Expected: only email feature, docs, and related verification changes.

- [ ] **Step 5: Commit the final verification/docs slice**

```bash
git add docs backend/tests frontend
git commit -m "docs: document email assistant feature"
```

## Execution Notes

- Keep scheduled email runs isolated from MongoDB checkpoints at all times.
- Prefer repository helpers for PostgreSQL access; do not push SQLAlchemy queries directly into routers.
- Keep the automatic notification stream separate from the chat SSE event contract.
- Avoid overbuilding provider-specific auth flows in phase one. IMAP + encrypted credentials is enough.
- If a real IMAP integration test is too brittle for CI, mock the IMAP client at the service layer and keep API/integration tests focused on persistence and routing.
