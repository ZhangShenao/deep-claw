from __future__ import annotations

import asyncio
import logging

from app.config import get_settings
from app.db import email_accounts as email_accounts_repo
from app.db.session import get_session
from app.email.client import ImapClientProtocol
from app.email.service import run_scheduled_email_check

logger = logging.getLogger(__name__)


async def run_due_account_checks_once(
    session,
    *,
    imap_client: ImapClientProtocol | None = None,
    limit: int = 5,
) -> int:
    account_ids = await email_accounts_repo.claim_due_account_ids(session, limit=limit)
    processed = 0
    for account_id in account_ids:
        await run_scheduled_email_check(session, account_id, imap_client=imap_client)
        processed += 1
    return processed


async def worker_loop() -> None:
    settings = get_settings()
    while True:
        try:
            async with get_session() as session:
                await run_due_account_checks_once(session, limit=5)
        except Exception:  # noqa: BLE001
            logger.exception("email worker cycle failed")
        await asyncio.sleep(settings.email_worker_poll_seconds)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()
