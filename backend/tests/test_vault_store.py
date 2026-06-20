from __future__ import annotations

import pytest

from app.core.vault_store import AuthenticationError, VaultStore


def test_initialize_unlock_and_persist_payload(tmp_path):
    store = VaultStore(tmp_path / "vault.senhas")
    data_key, payload, user = store.initialize(
        admin_username="admin",
        admin_password="AdminPass123!",
        viewer_username="user",
        viewer_password="ViewerPass123!",
    )

    assert user["role"] == "admin"
    assert payload["entries"] == []
    assert store.is_configured()

    viewer_key, viewer_payload, viewer = store.unlock("user", "ViewerPass123!")
    assert viewer["role"] == "viewer"
    assert viewer_payload["users"][1]["username"] == "user"

    payload["entries"].append(
        {
            "id": "entry-1",
            "title": "GitHub",
            "username": "dev@example.com",
            "secret": "senha-super-secreta",
            "url": "https://github.com",
            "category": "Dev",
            "notes": "",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }
    )
    store.persist_payload(data_key, payload)

    reloaded = store.load_payload(viewer_key)
    assert reloaded["entries"][0]["secret"] == "senha-super-secreta"


def test_wrong_password_does_not_unlock(tmp_path):
    store = VaultStore(tmp_path / "vault.senhas")
    store.initialize(
        admin_username="admin",
        admin_password="AdminPass123!",
        viewer_username="user",
        viewer_password="ViewerPass123!",
    )

    with pytest.raises(AuthenticationError):
        store.unlock("admin", "senha-errada")


def test_change_login_password_rewraps_user_key_slot(tmp_path):
    store = VaultStore(tmp_path / "vault.senhas")
    data_key, _, _ = store.initialize(
        admin_username="admin",
        admin_password="AdminPass123!",
        viewer_username="user",
        viewer_password="ViewerPass123!",
    )

    updated = store.change_login_password(
        data_key,
        target_username="user",
        new_password="NovaSenhaUser123!",
        actor_username="admin",
    )

    assert updated["username"] == "user"
    with pytest.raises(AuthenticationError):
        store.unlock("user", "ViewerPass123!")

    _, payload, user = store.unlock("user", "NovaSenhaUser123!")
    assert user["role"] == "viewer"
    assert payload["audit_logs"][-1]["action"] == "login_password_changed"

    _, _, admin = store.unlock("admin", "AdminPass123!")
    assert admin["role"] == "admin"
