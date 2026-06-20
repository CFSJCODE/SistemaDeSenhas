from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import get_vault_path
from app.core.crypto import (
    CryptoError,
    DATA_KEY_LEN,
    derive_key,
    encrypt_bytes,
    encrypt_json,
    decrypt_bytes,
    decrypt_json,
    new_kdf_config,
)

VAULT_FORMAT = "sistema-de-senhas-vault"
VAULT_VERSION = 1
PAYLOAD_AAD = b"sistema-de-senhas:payload:v1"


class VaultError(Exception):
    """Base class for vault persistence errors."""


class VaultAlreadyExistsError(VaultError):
    """Raised when setup is attempted on an existing vault."""


class VaultNotConfiguredError(VaultError):
    """Raised when the vault file has not been created yet."""


class AuthenticationError(VaultError):
    """Raised when a username or password cannot unlock the vault."""


class AuthorizationError(VaultError):
    """Raised when a user role cannot perform an operation."""


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_username(username: str) -> str:
    return username.strip().lower()


def default_payload(admin_username: str, viewer_username: str) -> dict[str, Any]:
    now = utc_now()
    return {
        "schema_version": 1,
        "users": [
            {
                "id": str(uuid4()),
                "username": admin_username,
                "role": "admin",
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": str(uuid4()),
                "username": viewer_username,
                "role": "viewer",
                "created_at": now,
                "updated_at": now,
            },
        ],
        "entries": [],
        "audit_logs": [
            {
                "id": str(uuid4()),
                "at": now,
                "username": admin_username,
                "action": "vault_created",
                "entry_id": None,
                "metadata": {"viewer": viewer_username},
            }
        ],
    }


class VaultStore:
    def __init__(self, vault_path: Path | None = None) -> None:
        self.vault_path = vault_path or get_vault_path()

    def is_configured(self) -> bool:
        return self.vault_path.exists()

    def initialize(
        self,
        *,
        admin_username: str,
        admin_password: str,
        viewer_username: str,
        viewer_password: str,
    ) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
        if self.is_configured():
            raise VaultAlreadyExistsError("The vault is already configured.")

        admin_username = normalize_username(admin_username)
        viewer_username = normalize_username(viewer_username)
        if not admin_username or not viewer_username:
            raise VaultError("Both usernames are required.")
        if admin_username == viewer_username:
            raise VaultError("Admin and viewer usernames must be different.")

        data_key = os.urandom(DATA_KEY_LEN)
        payload = default_payload(admin_username, viewer_username)
        payload_nonce, payload_ciphertext = encrypt_json(data_key, payload, PAYLOAD_AAD)
        now = utc_now()
        raw = {
            "format": VAULT_FORMAT,
            "version": VAULT_VERSION,
            "created_at": now,
            "updated_at": now,
            "payload_nonce": payload_nonce,
            "payload_ciphertext": payload_ciphertext,
            "key_slots": [
                self._make_key_slot(admin_username, admin_password, data_key),
                self._make_key_slot(viewer_username, viewer_password, data_key),
            ],
        }
        self._write_raw(raw)
        admin = self._find_payload_user(payload, admin_username)
        return data_key, deepcopy(payload), deepcopy(admin)

    def unlock(self, username: str, password: str) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
        username = normalize_username(username)
        raw = self._read_raw()
        slot = self._find_key_slot(raw, username)
        if slot is None:
            raise AuthenticationError("Invalid username or password.")

        try:
            password_key = derive_key(password, slot["kdf"])
            data_key = decrypt_bytes(
                password_key,
                slot["wrap_nonce"],
                slot["wrapped_key"],
                aad=f"key-slot:{username}".encode("utf-8"),
            )
            payload = self._decrypt_payload(raw, data_key)
            user = self._find_payload_user(payload, username)
        except (CryptoError, KeyError, TypeError) as exc:
            raise AuthenticationError("Invalid username or password.") from exc

        return data_key, payload, deepcopy(user)

    def load_payload(self, data_key: bytes) -> dict[str, Any]:
        return self._decrypt_payload(self._read_raw(), data_key)

    def persist_payload(self, data_key: bytes, payload: dict[str, Any]) -> None:
        raw = self._read_raw()
        payload_nonce, payload_ciphertext = encrypt_json(data_key, payload, PAYLOAD_AAD)
        raw["payload_nonce"] = payload_nonce
        raw["payload_ciphertext"] = payload_ciphertext
        raw["updated_at"] = utc_now()
        self._write_raw(raw)

    def change_login_password(
        self,
        data_key: bytes,
        *,
        target_username: str,
        new_password: str,
        actor_username: str,
    ) -> dict[str, Any]:
        target_username = normalize_username(target_username)
        actor_username = normalize_username(actor_username)
        raw = self._read_raw()
        payload = self._decrypt_payload(raw, data_key)
        user = self._find_payload_user(payload, target_username)

        raw["key_slots"] = self._replace_key_slot(raw, target_username, new_password, data_key)
        now = utc_now()
        user["updated_at"] = now
        payload.setdefault("audit_logs", []).append(
            {
                "id": str(uuid4()),
                "at": now,
                "username": actor_username,
                "action": "login_password_changed",
                "entry_id": None,
                "metadata": {"target_user": target_username, "target_role": user.get("role", "")},
            }
        )
        payload["audit_logs"] = payload["audit_logs"][-500:]

        payload_nonce, payload_ciphertext = encrypt_json(data_key, payload, PAYLOAD_AAD)
        raw["payload_nonce"] = payload_nonce
        raw["payload_ciphertext"] = payload_ciphertext
        raw["updated_at"] = now
        self._write_raw(raw)
        return deepcopy(user)

    def append_audit(
        self,
        data_key: bytes,
        *,
        username: str,
        action: str,
        entry_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        payload = self.load_payload(data_key)
        logs = payload.setdefault("audit_logs", [])
        logs.append(
            {
                "id": str(uuid4()),
                "at": utc_now(),
                "username": normalize_username(username),
                "action": action,
                "entry_id": entry_id,
                "metadata": metadata or {},
            }
        )
        payload["audit_logs"] = logs[-500:]
        self.persist_payload(data_key, payload)

    def _decrypt_payload(self, raw: dict[str, Any], data_key: bytes) -> dict[str, Any]:
        payload = decrypt_json(data_key, raw["payload_nonce"], raw["payload_ciphertext"], PAYLOAD_AAD)
        if payload.get("schema_version") != 1:
            raise CryptoError("Unsupported payload schema.")
        if not isinstance(payload.get("entries"), list):
            raise CryptoError("Payload entries must be a list.")
        if not isinstance(payload.get("users"), list):
            raise CryptoError("Payload users must be a list.")
        return payload

    def _read_raw(self) -> dict[str, Any]:
        if not self.vault_path.exists():
            raise VaultNotConfiguredError("The vault has not been configured yet.")

        try:
            raw = json.loads(self.vault_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise VaultError("Vault file could not be read.") from exc

        if raw.get("format") != VAULT_FORMAT or raw.get("version") != VAULT_VERSION:
            raise VaultError("Unsupported vault file format.")
        if not isinstance(raw.get("key_slots"), list):
            raise VaultError("Vault key slots are invalid.")
        return raw

    def _write_raw(self, raw: dict[str, Any]) -> None:
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{self.vault_path.name}.",
            suffix=".tmp",
            dir=str(self.vault_path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
                json.dump(raw, temp_file, ensure_ascii=False, separators=(",", ":"))
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_name, self.vault_path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def _make_key_slot(self, username: str, password: str, data_key: bytes) -> dict[str, Any]:
        kdf = new_kdf_config()
        password_key = derive_key(password, kdf)
        wrap_nonce, wrapped_key = encrypt_bytes(
            password_key,
            data_key,
            aad=f"key-slot:{username}".encode("utf-8"),
        )
        return {
            "username": username,
            "kdf": kdf,
            "wrap_nonce": wrap_nonce,
            "wrapped_key": wrapped_key,
        }

    def _replace_key_slot(
        self,
        raw: dict[str, Any],
        username: str,
        password: str,
        data_key: bytes,
    ) -> list[dict[str, Any]]:
        key_slots = list(raw.get("key_slots", []))
        replacement = self._make_key_slot(username, password, data_key)
        for index, slot in enumerate(key_slots):
            if slot.get("username") == username:
                key_slots[index] = replacement
                return key_slots

        key_slots.append(replacement)
        return key_slots

    @staticmethod
    def _find_key_slot(raw: dict[str, Any], username: str) -> dict[str, Any] | None:
        for slot in raw.get("key_slots", []):
            if slot.get("username") == username:
                return slot
        return None

    @staticmethod
    def _find_payload_user(payload: dict[str, Any], username: str) -> dict[str, Any]:
        for user in payload.get("users", []):
            if user.get("username") == username:
                return user
        raise AuthenticationError("Invalid username or password.")
