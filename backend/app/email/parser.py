from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr, parsedate_to_datetime


@dataclass(slots=True)
class NormalizedEmail:
    subject: str
    from_display: str
    from_address: str
    message_id_header: str
    received_at: datetime | None
    body_text: str
    snippet: str


def _extract_plain_text(message) -> str:
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in (part.get("Content-Disposition") or ""):
                return part.get_content()
        for part in message.walk():
            if part.get_content_type() == "text/html":
                return part.get_content()
        return ""
    return message.get_content()


def _trim_quoted_text(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(">") or stripped.startswith("On ") and stripped.endswith("wrote:"):
            break
        lines.append(line)
    return "\n".join(lines).strip()


def normalize_email_message(raw_bytes: bytes) -> NormalizedEmail:
    message = BytesParser(policy=policy.default).parsebytes(raw_bytes)
    from_display, from_address = parseaddr(message.get("From", ""))
    body_text = _trim_quoted_text(_extract_plain_text(message))
    compact = " ".join(body_text.split())
    snippet = compact[:160]

    return NormalizedEmail(
        subject=message.get("Subject", ""),
        from_display=from_display,
        from_address=from_address,
        message_id_header=message.get("Message-ID", ""),
        received_at=parsedate_to_datetime(message.get("Date")) if message.get("Date") else None,
        body_text=body_text,
        snippet=snippet,
    )
