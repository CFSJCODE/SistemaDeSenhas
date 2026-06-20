from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

Role = Literal["admin", "viewer"]


class StatusResponse(BaseModel):
    configured: bool
    vault_path: str


class SetupRequest(BaseModel):
    admin_username: str = Field(default="admin", min_length=3, max_length=40)
    admin_password: str = Field(min_length=8, max_length=256)
    viewer_username: str = Field(default="user", min_length=3, max_length=40)
    viewer_password: str = Field(min_length=8, max_length=256)

    @field_validator("admin_username", "viewer_username")
    @classmethod
    def normalize_usernames(cls, value: str) -> str:
        return value.strip().lower()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()


class AuthResponse(BaseModel):
    token: str
    username: str
    role: Role
    expires_at: str


class MeResponse(BaseModel):
    username: str
    role: Role
    expires_at: str


class EntryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    username: str = Field(default="", max_length=160)
    secret: str = Field(min_length=1, max_length=4096)
    url: str = Field(default="", max_length=500)
    category: str = Field(default="", max_length=80)
    notes: str = Field(default="", max_length=2000)


class EntryUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    username: str = Field(default="", max_length=160)
    secret: str | None = Field(default=None, min_length=1, max_length=4096)
    url: str = Field(default="", max_length=500)
    category: str = Field(default="", max_length=80)
    notes: str = Field(default="", max_length=2000)


class EntryRead(BaseModel):
    id: str
    title: str
    username: str = ""
    url: str = ""
    category: str = ""
    notes: str = ""
    created_at: str
    updated_at: str


class EntrySecretResponse(BaseModel):
    id: str
    secret: str


class AuditLogRead(BaseModel):
    id: str
    at: str
    username: str
    action: str
    entry_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UserRead(BaseModel):
    id: str
    username: str
    role: Role
    created_at: str
    updated_at: str


class LoginPasswordUpdate(BaseModel):
    new_password: str = Field(min_length=8, max_length=256)
