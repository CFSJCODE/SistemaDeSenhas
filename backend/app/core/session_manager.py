from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import RLock

from app.core.config import SESSION_TTL_MINUTES


@dataclass(frozen=True)
class Session:
    token: str
    username: str
    role: str
    data_key: bytes
    expires_at: datetime


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = RLock()

    def create(self, *, username: str, role: str, data_key: bytes) -> Session:
        token = secrets.token_urlsafe(32)
        session = Session(
            token=token,
            username=username,
            role=role,
            data_key=data_key,
            expires_at=datetime.now(UTC) + timedelta(minutes=SESSION_TTL_MINUTES),
        )
        with self._lock:
            self._sessions[token] = session
            self._prune_locked()
        return session

    def get(self, token: str) -> Session | None:
        with self._lock:
            session = self._sessions.get(token)
            if session is None:
                return None
            if session.expires_at <= datetime.now(UTC):
                self._sessions.pop(token, None)
                return None
            return session

    def delete(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(token, None)

    def delete_for_user(self, username: str, keep_token: str | None = None) -> None:
        with self._lock:
            tokens = [
                token
                for token, session in self._sessions.items()
                if session.username == username and token != keep_token
            ]
            for token in tokens:
                self._sessions.pop(token, None)

    def _prune_locked(self) -> None:
        now = datetime.now(UTC)
        expired = [token for token, session in self._sessions.items() if session.expires_at <= now]
        for token in expired:
            self._sessions.pop(token, None)
