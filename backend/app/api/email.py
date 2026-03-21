from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import EmailAccountCreate, EmailAccountOut
from app.db import email_accounts as email_accounts_repo
from app.db.session import get_db as db_session_dep

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
