from __future__ import annotations

from app.email.client import ImapClient


class FakeMailboxClient:
    def __init__(self) -> None:
        self.selected: list[str] = []

    def select(self, folder_name: str):
        self.selected.append(folder_name)
        if folder_name == "INBOX":
            return "NO", [b"Mailbox does not exist"]
        if folder_name == "Inbox":
            return "OK", [b"2"]
        raise AssertionError(f"unexpected folder selection: {folder_name}")

    def list(self):
        return "OK", [b'(\\HasNoChildren \\Inbox) "/" "Inbox"']

    def response(self, code: str):
        assert code == "UIDVALIDITY"
        return code, [b"777"]


def test_select_mailbox_falls_back_to_inbox_flagged_mailbox() -> None:
    client = ImapClient()
    fake = FakeMailboxClient()

    uid_validity = client._select_mailbox(fake, "INBOX")

    assert uid_validity == 777
    assert fake.selected == ["INBOX", "Inbox"]


class FakeUnsafeLoginClient:
    def __init__(self) -> None:
        self.selected: list[str] = []
        self.id_sent = False

    def xatom(self, name: str, *args: str):
        assert name == "ID"
        self.id_sent = True
        return "OK", [b"ID completed"]

    def select(self, folder_name: str):
        self.selected.append(folder_name)
        if not self.id_sent:
            return "NO", [b"SELECT Unsafe Login. Please contact kefu@188.com for help"]
        return "OK", [b"2"]

    def list(self):
        return "OK", [b'(\\HasNoChildren \\Inbox) "/" "INBOX"']

    def response(self, code: str):
        assert code == "UIDVALIDITY"
        return code, [b"888"]


def test_select_mailbox_sends_imap_id_and_retries_after_unsafe_login() -> None:
    client = ImapClient()
    fake = FakeUnsafeLoginClient()

    uid_validity = client._select_mailbox(fake, "INBOX")

    assert uid_validity == 888
    assert fake.id_sent is True
    assert fake.selected == ["INBOX", "INBOX"]
