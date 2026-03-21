from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import Settings


def _build_fernet(key_material: str) -> Fernet:
    digest = hashlib.sha256(key_material.encode("utf-8")).digest()
    token = base64.urlsafe_b64encode(digest)
    return Fernet(token)


def encrypt_secret(value: str, settings: Settings) -> str:
    signer = _build_fernet(settings.email_credential_key)
    return signer.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str, settings: Settings) -> str:
    signer = _build_fernet(settings.email_credential_key)
    return signer.decrypt(value.encode("utf-8")).decode("utf-8")
