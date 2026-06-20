from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_session, require_admin
from app.core.container import session_manager, vault_store
from app.core.session_manager import Session
from app.core.vault_store import (
    AuthenticationError,
    VaultAlreadyExistsError,
    VaultError,
    VaultNotConfiguredError,
    utc_now,
)
from app.models.schemas import (
    AuditLogRead,
    AuthResponse,
    EntryCreate,
    EntryRead,
    EntrySecretResponse,
    EntryUpdate,
    LoginPasswordUpdate,
    LoginRequest,
    MeResponse,
    SetupRequest,
    StatusResponse,
    UserRead,
)

router = APIRouter()


@router.get("/status", response_model=StatusResponse)
def status_check() -> StatusResponse:
    return StatusResponse(configured=vault_store.is_configured(), vault_path=str(vault_store.vault_path))


@router.post("/setup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def setup_vault(payload: SetupRequest) -> AuthResponse:
    try:
        data_key, _, user = vault_store.initialize(
            admin_username=payload.admin_username,
            admin_password=payload.admin_password,
            viewer_username=payload.viewer_username,
            viewer_password=payload.viewer_password,
        )
    except VaultAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except VaultError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    session = session_manager.create(username=user["username"], role=user["role"], data_key=data_key)
    return _auth_response(session)


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    try:
        data_key, _, user = vault_store.unlock(payload.username, payload.password)
    except VaultNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    session = session_manager.create(username=user["username"], role=user["role"], data_key=data_key)
    try:
        vault_store.append_audit(session.data_key, username=session.username, action="login")
    except VaultError:
        pass
    return _auth_response(session)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(session: Session = Depends(get_current_session)) -> None:
    session_manager.delete(session.token)


@router.get("/auth/me", response_model=MeResponse)
def me(session: Session = Depends(get_current_session)) -> MeResponse:
    return MeResponse(
        username=session.username,
        role=session.role,
        expires_at=session.expires_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
    )


@router.get("/passwords", response_model=list[EntryRead])
def list_passwords(session: Session = Depends(get_current_session)) -> list[EntryRead]:
    payload = vault_store.load_payload(session.data_key)
    entries = sorted(payload.get("entries", []), key=lambda item: item.get("title", "").lower())
    return [EntryRead(**_public_entry(entry)) for entry in entries]


@router.get("/passwords/{entry_id}/secret", response_model=EntrySecretResponse)
def reveal_password(entry_id: str, session: Session = Depends(get_current_session)) -> EntrySecretResponse:
    payload = vault_store.load_payload(session.data_key)
    entry = _find_entry(payload, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Password entry not found.")

    vault_store.append_audit(
        session.data_key,
        username=session.username,
        action="secret_revealed",
        entry_id=entry_id,
        metadata={"title": entry.get("title", "")},
    )
    return EntrySecretResponse(id=entry_id, secret=entry["secret"])


@router.post("/passwords", response_model=EntryRead, status_code=status.HTTP_201_CREATED)
def create_password(payload: EntryCreate, session: Session = Depends(require_admin)) -> EntryRead:
    vault_payload = vault_store.load_payload(session.data_key)
    now = utc_now()
    entry = {
        "id": str(uuid4()),
        "title": payload.title.strip(),
        "username": payload.username.strip(),
        "secret": payload.secret,
        "url": payload.url.strip(),
        "category": payload.category.strip(),
        "notes": payload.notes.strip(),
        "created_at": now,
        "updated_at": now,
    }
    vault_payload.setdefault("entries", []).append(entry)
    _append_audit_to_payload(
        vault_payload,
        username=session.username,
        action="entry_created",
        entry_id=entry["id"],
        metadata={"title": entry["title"]},
    )
    vault_store.persist_payload(session.data_key, vault_payload)
    return EntryRead(**_public_entry(entry))


@router.put("/passwords/{entry_id}", response_model=EntryRead)
def update_password(entry_id: str, payload: EntryUpdate, session: Session = Depends(require_admin)) -> EntryRead:
    vault_payload = vault_store.load_payload(session.data_key)
    entry = _find_entry(vault_payload, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Password entry not found.")

    entry["title"] = payload.title.strip()
    entry["username"] = payload.username.strip()
    entry["url"] = payload.url.strip()
    entry["category"] = payload.category.strip()
    entry["notes"] = payload.notes.strip()
    if payload.secret is not None:
        entry["secret"] = payload.secret
    entry["updated_at"] = utc_now()
    _append_audit_to_payload(
        vault_payload,
        username=session.username,
        action="entry_updated",
        entry_id=entry_id,
        metadata={"title": entry["title"]},
    )
    vault_store.persist_payload(session.data_key, vault_payload)
    return EntryRead(**_public_entry(entry))


@router.delete("/passwords/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_password(entry_id: str, session: Session = Depends(require_admin)) -> None:
    vault_payload = vault_store.load_payload(session.data_key)
    entries = vault_payload.get("entries", [])
    entry = _find_entry(vault_payload, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Password entry not found.")

    vault_payload["entries"] = [item for item in entries if item.get("id") != entry_id]
    _append_audit_to_payload(
        vault_payload,
        username=session.username,
        action="entry_deleted",
        entry_id=entry_id,
        metadata={"title": entry.get("title", "")},
    )
    vault_store.persist_payload(session.data_key, vault_payload)


@router.get("/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs(session: Session = Depends(require_admin)) -> list[AuditLogRead]:
    payload = vault_store.load_payload(session.data_key)
    logs = list(reversed(payload.get("audit_logs", [])))
    return [AuditLogRead(**log) for log in logs[:200]]


@router.get("/users", response_model=list[UserRead])
def list_users(session: Session = Depends(require_admin)) -> list[UserRead]:
    payload = vault_store.load_payload(session.data_key)
    return [UserRead(**user) for user in payload.get("users", [])]


@router.put("/users/{username}/password", response_model=UserRead)
def change_user_login_password(
    username: str,
    payload: LoginPasswordUpdate,
    session: Session = Depends(require_admin),
) -> UserRead:
    try:
        user = vault_store.change_login_password(
            session.data_key,
            target_username=username,
            new_password=payload.new_password,
            actor_username=session.username,
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.") from exc
    except VaultError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    keep_token = session.token if user["username"] == session.username else None
    session_manager.delete_for_user(user["username"], keep_token=keep_token)
    return UserRead(**user)


def _auth_response(session: Session) -> AuthResponse:
    return AuthResponse(
        token=session.token,
        username=session.username,
        role=session.role,
        expires_at=session.expires_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
    )


def _public_entry(entry: dict) -> dict:
    public = deepcopy(entry)
    public.pop("secret", None)
    return public


def _find_entry(payload: dict, entry_id: str) -> dict | None:
    for entry in payload.get("entries", []):
        if entry.get("id") == entry_id:
            return entry
    return None


def _append_audit_to_payload(
    payload: dict,
    *,
    username: str,
    action: str,
    entry_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    logs = payload.setdefault("audit_logs", [])
    logs.append(
        {
            "id": str(uuid4()),
            "at": utc_now(),
            "username": username,
            "action": action,
            "entry_id": entry_id,
            "metadata": metadata or {},
        }
    )
    payload["audit_logs"] = logs[-500:]
