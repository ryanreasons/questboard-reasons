from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
import shutil

import pytest
from fastapi import HTTPException, Response
from fastapi.testclient import TestClient

from backend import auth
from backend.auth import BootstrapRequest, utc_now, utc_text
from backend.database import connect, initialize_database
from backend.main import app


PARENT_PASSWORD = "correct horse battery staple"
CHILD_PASSWORD = "another long child passphrase"


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    db_path = tmp_path / "questboard.db"
    monkeypatch.setenv("QUESTBOARD_DB", str(db_path))
    monkeypatch.setenv("QUESTBOARD_DATA", str(tmp_path))
    monkeypatch.setenv("QUESTBOARD_SECURE_COOKIES", "false")
    monkeypatch.setenv("QUESTBOARD_SESSION_HOURS", "24")

    with TestClient(app) as client:
        yield client, db_path


def bootstrap_parent(client, username="parent"):
    response = client.post(
        "/auth/bootstrap",
        json={"username": username, "password": PARENT_PASSWORD},
    )
    assert response.status_code == 201, response.text
    return response


def test_bootstrap_creates_hashed_parent_and_httponly_session(auth_client):
    client, db_path = auth_client

    status = client.get("/auth/bootstrap-status")
    assert status.status_code == 200
    assert status.json() == {"needs_bootstrap": True}

    response = bootstrap_parent(client, "Parent.User")
    user = response.json()["user"]
    assert user["username"] == "parent.user"
    assert user["role"] == "parent"
    assert "password_hash" not in user
    assert "token_hash" not in user

    cookie_header = response.headers["set-cookie"].lower()
    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header
    assert "path=/" in cookie_header
    assert "secure" not in cookie_header

    raw_token = client.cookies.get(auth.SESSION_COOKIE)
    assert raw_token

    with connect(str(db_path)) as conn:
        db_user = conn.execute(
            "SELECT username, password_hash, role FROM users"
        ).fetchone()
        assert db_user["username"] == "parent.user"
        assert db_user["role"] == "parent"
        assert db_user["password_hash"] != PARENT_PASSWORD
        assert db_user["password_hash"].startswith("$argon2")

        session = conn.execute(
            "SELECT token_hash FROM sessions"
        ).fetchone()
        assert session["token_hash"] != raw_token
        assert session["token_hash"] == auth.hash_session_token(raw_token)

    assert client.get("/auth/bootstrap-status").json() == {
        "needs_bootstrap": False
    }
    second = client.post(
        "/auth/bootstrap",
        json={"username": "other", "password": PARENT_PASSWORD},
    )
    assert second.status_code == 409


def test_login_me_logout_and_generic_invalid_credentials(auth_client):
    client, db_path = auth_client
    bootstrap_parent(client)
    assert client.post("/auth/logout").status_code == 200

    unknown = client.post(
        "/auth/login",
        json={"username": "nobody", "password": "totally wrong password"},
    )
    wrong = client.post(
        "/auth/login",
        json={"username": "parent", "password": "totally wrong password"},
    )
    assert unknown.status_code == 401
    assert wrong.status_code == 401
    assert unknown.json() == wrong.json() == {"detail": "invalid credentials"}

    good = client.post(
        "/auth/login",
        json={"username": "PARENT", "password": PARENT_PASSWORD},
    )
    assert good.status_code == 200
    assert good.json()["user"]["username"] == "parent"

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["role"] == "parent"

    token_hash = auth.hash_session_token(client.cookies.get(auth.SESSION_COOKIE))
    logout = client.post("/auth/logout")
    assert logout.status_code == 200
    assert client.get("/auth/me").status_code == 401

    with connect(str(db_path)) as conn:
        assert conn.execute(
            "SELECT revoked_at FROM sessions WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()[0] is not None


def test_parent_user_management_and_child_authorization(auth_client):
    client, _ = auth_client
    bootstrap_parent(client)

    created = client.post(
        "/auth/users",
        json={
            "username": "child.one",
            "password": CHILD_PASSWORD,
            "role": "child",
        },
    )
    assert created.status_code == 201, created.text
    child_id = created.json()["user"]["id"]

    users = client.get("/auth/users")
    assert users.status_code == 200
    assert len(users.json()["users"]) == 2

    assert client.post("/auth/logout").status_code == 200
    assert client.post(
        "/auth/login",
        json={"username": "child.one", "password": CHILD_PASSWORD},
    ).status_code == 200

    assert client.get("/auth/users").status_code == 403
    assert client.post(
        "/auth/users",
        json={
            "username": "forbidden",
            "password": CHILD_PASSWORD,
            "role": "child",
        },
    ).status_code == 403
    assert client.patch(
        f"/auth/users/{child_id}/active",
        json={"is_active": False},
    ).status_code == 403


def test_disable_and_password_reset_revoke_sessions(auth_client):
    parent_client, _ = auth_client
    bootstrap_parent(parent_client)
    created = parent_client.post(
        "/auth/users",
        json={
            "username": "child",
            "password": CHILD_PASSWORD,
            "role": "child",
        },
    )
    child_id = created.json()["user"]["id"]

    with TestClient(app) as child_client:
        login = child_client.post(
            "/auth/login",
            json={"username": "child", "password": CHILD_PASSWORD},
        )
        assert login.status_code == 200
        assert child_client.get("/auth/me").status_code == 200

        disabled = parent_client.patch(
            f"/auth/users/{child_id}/active",
            json={"is_active": False},
        )
        assert disabled.status_code == 200
        assert child_client.get("/auth/me").status_code == 401
        assert child_client.post(
            "/auth/login",
            json={"username": "child", "password": CHILD_PASSWORD},
        ).status_code == 401

        assert parent_client.patch(
            f"/auth/users/{child_id}/active",
            json={"is_active": True},
        ).status_code == 200
        assert child_client.post(
            "/auth/login",
            json={"username": "child", "password": CHILD_PASSWORD},
        ).status_code == 200

        reset = parent_client.post(
            f"/auth/users/{child_id}/reset-password",
            json={"password": "brand new long child password"},
        )
        assert reset.status_code == 200
        assert child_client.get("/auth/me").status_code == 401
        assert child_client.post(
            "/auth/login",
            json={"username": "child", "password": CHILD_PASSWORD},
        ).status_code == 401
        assert child_client.post(
            "/auth/login",
            json={
                "username": "child",
                "password": "brand new long child password",
            },
        ).status_code == 200


def test_cannot_disable_last_active_parent(auth_client):
    client, _ = auth_client
    first = bootstrap_parent(client)
    parent_id = first.json()["user"]["id"]

    blocked = client.patch(
        f"/auth/users/{parent_id}/active",
        json={"is_active": False},
    )
    assert blocked.status_code == 409

    second = client.post(
        "/auth/users",
        json={
            "username": "parent.two",
            "password": PARENT_PASSWORD,
            "role": "parent",
        },
    )
    assert second.status_code == 201

    allowed = client.patch(
        f"/auth/users/{parent_id}/active",
        json={"is_active": False},
    )
    assert allowed.status_code == 200


def test_expired_session_is_rejected(auth_client):
    client, db_path = auth_client
    bootstrap_parent(client)
    token = client.cookies.get(auth.SESSION_COOKIE)
    token_hash = auth.hash_session_token(token)

    with connect(str(db_path)) as conn:
        conn.execute(
            "UPDATE sessions SET expires_at = ? WHERE token_hash = ?",
            (utc_text(utc_now() - timedelta(hours=1)), token_hash),
        )

    assert client.get("/auth/me").status_code == 401
    with connect(str(db_path)) as conn:
        assert conn.execute(
            "SELECT revoked_at FROM sessions WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()[0] is not None


def test_password_policy_and_username_canonicalization(auth_client):
    client, _ = auth_client

    short = client.post(
        "/auth/bootstrap",
        json={"username": "parent", "password": "too short"},
    )
    assert short.status_code == 422

    good = client.post(
        "/auth/bootstrap",
        json={"username": "  PARENT.User  ", "password": PARENT_PASSWORD},
    )
    assert good.status_code == 201
    assert good.json()["user"]["username"] == "parent.user"

    duplicate = client.post(
        "/auth/users",
        json={
            "username": "Parent.User",
            "password": CHILD_PASSWORD,
            "role": "child",
        },
    )
    assert duplicate.status_code == 409


def test_bootstrap_race_creates_exactly_one_parent(tmp_path, monkeypatch):
    db_path = tmp_path / "questboard.db"
    monkeypatch.setenv("QUESTBOARD_DB", str(db_path))
    monkeypatch.setenv("QUESTBOARD_DATA", str(tmp_path))
    monkeypatch.setenv("QUESTBOARD_SESSION_HOURS", "24")
    initialize_database()

    def attempt(index):
        try:
            result = auth.bootstrap(
                BootstrapRequest(
                    username=f"parent{index}",
                    password=PARENT_PASSWORD,
                ),
                Response(),
            )
            return "ok", result["user"]["id"]
        except HTTPException as exc:
            return "error", exc.status_code

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(attempt, range(5)))

    assert sum(1 for status, _ in results if status == "ok") == 1
    assert sum(1 for status, code in results if status == "error" and code == 409) == 4

    with connect(str(db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'parent' AND is_active = 1"
        ).fetchone()[0] == 1


def test_upgrade_from_001_preserves_existing_data(tmp_path, monkeypatch):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    real_migrations = Path(__file__).resolve().parents[1] / "migrations"
    shutil.copy(real_migrations / "001_initial.sql", migrations_dir / "001_initial.sql")

    db_path = tmp_path / "questboard.db"
    monkeypatch.setenv("QUESTBOARD_DB", str(db_path))
    monkeypatch.setattr("backend.database.MIGRATIONS_DIR", migrations_dir)

    initialize_database()
    with connect(str(db_path)) as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?)",
            ("preserve-me", "yes"),
        )

    shutil.copy(real_migrations / "002_auth.sql", migrations_dir / "002_auth.sql")
    initialize_database()

    with connect(str(db_path)) as conn:
        assert conn.execute(
            "SELECT value FROM app_settings WHERE key = 'preserve-me'"
        ).fetchone()[0] == "yes"
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(users)")
        }
        assert "last_login_at" in columns
        applied = [
            row[0]
            for row in conn.execute(
                "SELECT filename FROM schema_migrations ORDER BY filename"
            )
        ]
        assert applied == ["001_initial.sql", "002_auth.sql"]


def test_secure_cookie_setting_is_configurable(auth_client, monkeypatch):
    client, _ = auth_client
    monkeypatch.setenv("QUESTBOARD_SECURE_COOKIES", "true")
    response = bootstrap_parent(client)
    assert "secure" in response.headers["set-cookie"].lower()
