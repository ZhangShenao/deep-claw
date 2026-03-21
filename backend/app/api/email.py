import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import EmailAccountCreate, EmailAccountOut, EmailCheckResultOut, EmailDigestOut
from app.db import email_accounts as email_accounts_repo
from app.db import email_messages as email_messages_repo
from app.db.session import get_db as db_session_dep
from app.email.service import run_manual_email_check

router = APIRouter(tags=["email"])
get_db = db_session_dep


@router.get("/api/email/accounts", response_model=list[EmailAccountOut])
async def list_email_accounts(session: AsyncSession = Depends(get_db)) -> list[EmailAccountOut]:
    rows = await email_accounts_repo.list_accounts(session)
    return [EmailAccountOut.model_validate(row) for row in rows]


@router.post("/api/email/accounts", response_model=EmailAccountOut)
async def create_email_account(
    body: EmailAccountCreate,
    session: AsyncSession = Depends(get_db),
) -> EmailAccountOut:
    row = await email_accounts_repo.create_account(session, body)
    return EmailAccountOut.model_validate(row)


@router.get("/api/email/digests", response_model=list[EmailDigestOut])
async def list_email_digests(session: AsyncSession = Depends(get_db)) -> list[EmailDigestOut]:
    rows = await email_messages_repo.list_digests(session)
    return [EmailDigestOut.model_validate(row) for row in rows]


@router.post("/api/email/accounts/{account_id}/check-now", response_model=EmailCheckResultOut)
async def check_email_now(
    account_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> EmailCheckResultOut:
    try:
        result = await run_manual_email_check(session, account_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return EmailCheckResultOut(
        digest_id=result.digest_id,
        account_id=result.account_id,
        trigger_source=result.trigger_source,
        new_message_count=result.new_message_count,
        summary=result.summary,
    )
