from __future__ import annotations

import asyncio
import imaplib
import re
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class ImapMessageEnvelope:
    uid: int
    raw_message: bytes
    flags: list[str]


@dataclass(slots=True)
class ImapFetchResult:
    uid_validity: int | None
    messages: list[ImapMessageEnvelope]


class ImapClientProtocol(Protocol):
    async def validate_connection(
        self,
        *,
        host: str,
        port: int,
        username: str,
        credential: str,
        folder_name: str,
    ) -> None: ...

    async def fetch_new_messages(
        self,
        *,
        host: str,
        port: int,
        username: str,
        credential: str,
        folder_name: str,
        last_seen_uid: int | None,
    ) -> ImapFetchResult: ...


class ImapClient:
    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds

    async def validate_connection(
        self,
        *,
        host: str,
        port: int,
        username: str,
        credential: str,
        folder_name: str,
    ) -> None:
        await asyncio.to_thread(
            self._validate_connection_blocking,
            host,
            port,
            username,
            credential,
            folder_name,
        )

    async def fetch_new_messages(
        self,
        *,
        host: str,
        port: int,
        username: str,
        credential: str,
        folder_name: str,
        last_seen_uid: int | None,
    ) -> ImapFetchResult:
        return await asyncio.to_thread(
            self._fetch_new_messages_blocking,
            host,
            port,
            username,
            credential,
            folder_name,
            last_seen_uid,
        )

    def _connect(self, host: str, port: int) -> imaplib.IMAP4_SSL:
        return imaplib.IMAP4_SSL(host=host, port=port, timeout=self.timeout_seconds)

    def _send_client_id(self, client: imaplib.IMAP4_SSL) -> None:
        try:
            client.xatom("ID", '("name" "Deep-Claw" "version" "0.1" "vendor" "OpenAI")')
        except Exception:
            pass

    def _is_unsafe_login_response(self, data: object) -> bool:
        if not data:
            return False
        if isinstance(data, (list, tuple)):
            parts = []
            for item in data:
                if isinstance(item, bytes):
                    parts.append(item.decode("utf-8", errors="ignore"))
                else:
                    parts.append(str(item))
            text = " ".join(parts)
        elif isinstance(data, bytes):
            text = data.decode("utf-8", errors="ignore")
        else:
            text = str(data)
        return "unsafe login" in text.lower()

    def _extract_mailbox_name(self, raw_line: bytes) -> str | None:
        decoded = raw_line.decode("utf-8", errors="ignore").strip()
        matches = re.findall(r'"([^"]+)"', decoded)
        if matches:
            return matches[-1]
        return None

    def _discover_mailbox_candidates(self, client: imaplib.IMAP4_SSL, folder_name: str) -> list[str]:
        candidates: list[str] = []
        if folder_name:
            candidates.append(folder_name)

        try:
            status, data = client.list()
        except Exception:
            return candidates
        if status != "OK" or not data:
            return candidates

        for item in data:
            if not isinstance(item, bytes):
                continue
            decoded = item.decode("utf-8", errors="ignore")
            mailbox_name = self._extract_mailbox_name(item)
            if mailbox_name is None:
                continue
            lowered = mailbox_name.lower()
            if "\\inbox" in decoded.lower() or lowered == "inbox" or mailbox_name in {"收件箱", "Inbox"}:
                if mailbox_name not in candidates:
                    candidates.append(mailbox_name)

        return candidates

    def _select_mailbox(self, client: imaplib.IMAP4_SSL, folder_name: str) -> int | None:
        last_error: tuple[str, object] | None = None
        for candidate in self._discover_mailbox_candidates(client, folder_name):
            status, data = client.select(candidate)
            if status != "OK" and self._is_unsafe_login_response(data):
                self._send_client_id(client)
                status, data = client.select(candidate)
            if status == "OK":
                response = client.response("UIDVALIDITY")
                if not response or not response[1]:
                    return None
                value = response[1][0]
                if isinstance(value, bytes):
                    value = value.decode("utf-8", errors="ignore")
                try:
                    return int(str(value))
                except ValueError:
                    return None
            last_error = (candidate, data)

        if last_error is None:
            raise RuntimeError(f"failed to select mailbox {folder_name}")
        candidate, data = last_error
        detail = data[0].decode("utf-8", errors="ignore") if data and isinstance(data[0], bytes) else str(data)
        raise RuntimeError(f"failed to select mailbox {candidate}: {detail}")

    def _validate_connection_blocking(
        self,
        host: str,
        port: int,
        username: str,
        credential: str,
        folder_name: str,
    ) -> None:
        client = self._connect(host, port)
        try:
            client.login(username, credential)
            self._select_mailbox(client, folder_name)
        finally:
            try:
                client.logout()
            except Exception:
                pass

    def _fetch_new_messages_blocking(
        self,
        host: str,
        port: int,
        username: str,
        credential: str,
        folder_name: str,
        last_seen_uid: int | None,
    ) -> ImapFetchResult:
        client = self._connect(host, port)
        try:
            client.login(username, credential)
            uid_validity = self._select_mailbox(client, folder_name)
            start_uid = (last_seen_uid or 0) + 1
            status, data = client.uid("search", None, f"{start_uid}:*")
            if status != "OK":
                raise RuntimeError("failed to search mailbox by uid")

            uid_tokens = []
            if data and data[0]:
                uid_tokens = [token for token in data[0].split() if token]

            messages: list[ImapMessageEnvelope] = []
            for token in uid_tokens:
                uid = int(token)
                fetch_status, fetch_data = client.uid("fetch", token, "(RFC822 FLAGS)")
                if fetch_status != "OK" or not fetch_data:
                    continue
                raw_message = b""
                flags: list[str] = []
                for item in fetch_data:
                    if not isinstance(item, tuple):
                        continue
                    meta, body = item
                    if isinstance(body, bytes):
                        raw_message = body
                    if isinstance(meta, bytes):
                        match = re.search(rb"FLAGS \((.*?)\)", meta)
                        if match:
                            flags = match.group(1).decode("utf-8", errors="ignore").split()
                if raw_message:
                    messages.append(ImapMessageEnvelope(uid=uid, raw_message=raw_message, flags=flags))

            return ImapFetchResult(uid_validity=uid_validity, messages=messages)
        finally:
            try:
                client.logout()
            except Exception:
                pass
