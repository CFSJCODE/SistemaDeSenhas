from __future__ import annotations

import base64
import json
import os
from typing import Any

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ARGON2_TIME_COST = int(os.getenv("SDS_ARGON2_TIME_COST", "3"))
ARGON2_MEMORY_COST_KIB = int(os.getenv("SDS_ARGON2_MEMORY_COST_KIB", "65536"))
ARGON2_PARALLELISM = int(os.getenv("SDS_ARGON2_PARALLELISM", "2"))
ARGON2_HASH_LEN = 32
SALT_LEN = 16
NONCE_LEN = 12
DATA_KEY_LEN = 32


class CryptoError(Exception):
    """Raised when encrypted content cannot be opened or validated."""


def b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii")


def b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode("ascii"))


def new_kdf_config() -> dict[str, Any]:
    return {
        "name": "argon2id",
        "salt": b64encode(os.urandom(SALT_LEN)),
        "time_cost": ARGON2_TIME_COST,
        "memory_cost_kib": ARGON2_MEMORY_COST_KIB,
        "parallelism": ARGON2_PARALLELISM,
        "hash_len": ARGON2_HASH_LEN,
    }


def derive_key(password: str, kdf: dict[str, Any]) -> bytes:
    if kdf.get("name") != "argon2id":
        raise CryptoError("Unsupported key derivation function.")

    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=b64decode(kdf["salt"]),
        time_cost=int(kdf["time_cost"]),
        memory_cost=int(kdf["memory_cost_kib"]),
        parallelism=int(kdf["parallelism"]),
        hash_len=int(kdf["hash_len"]),
        type=Type.ID,
    )


def encrypt_bytes(key: bytes, raw: bytes, aad: bytes | None = None) -> tuple[str, str]:
    nonce = os.urandom(NONCE_LEN)
    ciphertext = AESGCM(key).encrypt(nonce, raw, aad)
    return b64encode(nonce), b64encode(ciphertext)


def decrypt_bytes(key: bytes, nonce: str, ciphertext: str, aad: bytes | None = None) -> bytes:
    try:
        return AESGCM(key).decrypt(b64decode(nonce), b64decode(ciphertext), aad)
    except InvalidTag as exc:
        raise CryptoError("Encrypted data could not be authenticated.") from exc


def encrypt_json(key: bytes, payload: dict[str, Any], aad: bytes | None = None) -> tuple[str, str]:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return encrypt_bytes(key, raw, aad)


def decrypt_json(key: bytes, nonce: str, ciphertext: str, aad: bytes | None = None) -> dict[str, Any]:
    raw = decrypt_bytes(key, nonce, ciphertext, aad)
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CryptoError("Encrypted payload is not valid JSON.") from exc

    if not isinstance(decoded, dict):
        raise CryptoError("Encrypted payload must be a JSON object.")

    return decoded
