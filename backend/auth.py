from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from pwdlib import PasswordHash

try:
    from .database import connect
except ImportError:  # Docker runtime imports modules from /app directly.
    from database import connect


router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE = "qb_session"
PASSWORD_MIN_CODEPOINTS = 15
PASSWORD_MAX_CODEPOINTS = 256
USERNAME_MIN_CODEPOINTS = 3
USERNAME_MAX_CODEPOINTS = 64

PASSWORD_HASHER = PasswordHash.recommended()
# Used only to make unknown-user login attempts perform Argon2 work too.
DUMMY_PASSWORD_HASH = PASSWORD_HASHER.hash(
    "questboard-dummy-password-not-a-real-account"
)


@dataclass(frozen=True)
class AuthUser:
    id: str
    username: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str
    last_login_at: str | None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_text(value: datetime | None = None) -> str:
    value = value or utc_now()
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def secure_cookies_enabled() -> bool:
    raw = os.environ.get("QUESTBOARD_SECURE_COOKIES", "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def session_hours() -> int:
    raw = os.environ.get("QUESTBOARD_SESSION_HOURS", "168")
    try:
        hours = int(raw)
    except ValueError as exc:
        raise RuntimeError("QUESTBOARD_SESSION_HOURS must be an integer") from exc
    if not 1 <= hours <= 24 * 90:
        raise RuntimeError("QUESTBOARD_SESSION_HOURS must be between 1 and 2160")
    return hours


def normalize_username(value: str) -> str:
    username = unicodedata.normalize("NFC", value).strip().casefold()
    if not (USERNAME_MIN_CODEPOINTS <= len(username) <= USERNAME_MAX_CODEPOINTS):
        raise ValueError("username must be 3-64 characters")
    if not all(ch.isalnum() or ch in "_.-" for ch in username):
        raise ValueError(
            "username may contain letters, numbers, dot, dash, or underscore"
        )
    return username


def normalize_password(value: str, *, enforce_minimum: bool) -> str:
    password = unicodedata.normalize("NFC", value)
    if len(password) > PASSWORD_MAX_CODEPOINTS:
        raise ValueError("password is too long")
    if enforce_minimum and len(password) < PASSWORD_MIN_CODEPOINTS:
        raise ValueError("password must be at least 15 characters")
    return password


def hash_password(value: str) -> str:
    password = normalize_password(value, enforce_minimum=True)
    return PASSWORD_HASHER.hash(password)


def verify_password(value: str, password_hash: str) -> bool:
    try:
        password = normalize_password(value, enforce_minimum=False)
        return bool(PASSWORD_HASHER.verify(password, password_hash))
    except Exception:
        return False


def new_user_id() -> str:
    return secrets.token_hex(16)


def new_session_id() -> str:
    return secrets.token_hex(16)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _http_422(message: str) -> HTTPException:
    return HTTPException(status_code=422, detail=message)


def _public_user(row: sqlite3.Row | AuthUser) -> dict[str, object]:
    return {
        "id": row["id"] if isinstance(row, sqlite3.Row) else row.id,
        "username": row["username"] if isinstance(row, sqlite3.Row) else row.username,
        "role": row["role"] if isinstance(row, sqlite3.Row) else row.role,
        "is_active": bool(
            row["is_active"] if isinstance(row, sqlite3.Row) else row.is_active
        ),
        "created_at": (
            row["created_at"] if isinstance(row, sqlite3.Row) else row.created_at
        ),
        "updated_at": (
            row["updated_at"] if isinstance(row, sqlite3.Row) else row.updated_at
        ),
        "last_login_at": (
            row["last_login_at"]
            if isinstance(row, sqlite3.Row)
            else row.last_login_at
        ),
    }


def _fetch_user_by_username(conn: sqlite3.Connection, username: str):
    return conn.execute(
        """
        SELECT id, username, password_hash, role, is_active,
               created_at, updated_at, last_login_at
        FROM users
        WHERE username = ?
        """,
        (username,),
    ).fetchone()


def _fetch_user_by_id(conn: sqlite3.Connection, user_id: str):
    return conn.execute(
        """
        SELECT id, username, password_hash, role, is_active,
               created_at, updated_at, last_login_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()


def _create_user(
    conn: sqlite3.Connection,
    *,
    username: str,
    password: str,
    role: Literal["parent", "child"],
) -> sqlite3.Row:
    try:
        canonical_username = normalize_username(username)
        password_hash = hash_password(password)
    except ValueError as exc:
        raise _http_422(str(exc)) from exc

    now = utc_text()
    user_id = new_user_id()
    try:
        conn.execute(
            """
            INSERT INTO users (
                id, username, password_hash, role, is_active,
                created_at, updated_at, last_login_at
            )
            VALUES (?, ?, ?, ?, 1, ?, ?, NULL)
            """,
            (
                user_id,
                canonical_username,
                password_hash,
                role,
                now,
                now,
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="username already exists") from exc

    row = _fetch_user_by_id(conn, user_id)
    if row is None:
        raise HTTPException(status_code=500, detail="failed to create user")
    return row


def _create_session(
    conn: sqlite3.Connection,
    user_id: str,
) -> tuple[str, datetime]:
    token = new_session_token()
    token_hash = hash_session_token(token)
    now = utc_now()
    expires = now + timedelta(hours=session_hours())

    conn.execute(
        """
        INSERT INTO sessions (
            id, user_id, token_hash, expires_at,
            created_at, last_seen_at, revoked_at
        )
        VALUES (?, ?, ?, ?, ?, ?, NULL)
        """,
        (
            new_session_id(),
            user_id,
            token_hash,
            utc_text(expires),
            utc_text(now),
            utc_text(now),
        ),
    )
    conn.execute(
        "UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?",
        (utc_text(now), utc_text(now), user_id),
    )
    return token, expires


def _set_session_cookie(response: Response, token: str, expires: datetime) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure_cookies_enabled(),
        path="/",
        max_age=session_hours() * 3600,
        expires=expires,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        secure=secure_cookies_enabled(),
        httponly=True,
        samesite="lax",
    )


def _lookup_session_user(token: str) -> tuple[sqlite3.Row, sqlite3.Row] | None:
    token_hash = hash_session_token(token)
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                s.id AS session_id,
                s.expires_at,
                s.revoked_at,
                u.id,
                u.username,
                u.password_hash,
                u.role,
                u.is_active,
                u.created_at,
                u.updated_at,
                u.last_login_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
            """,
            (token_hash,),
        ).fetchone()
        if row is None:
            return None

        if row["revoked_at"] is not None or not bool(row["is_active"]):
            return None

        if parse_utc(row["expires_at"]) <= utc_now():
            conn.execute(
                "UPDATE sessions SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
                (utc_text(), row["session_id"]),
            )
            return None

        conn.execute(
            "UPDATE sessions SET last_seen_at = ? WHERE id = ?",
            (utc_text(), row["session_id"]),
        )
        return row, row


def get_current_user(request: Request) -> AuthUser:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="authentication required")

    found = _lookup_session_user(token)
    if found is None:
        raise HTTPException(status_code=401, detail="authentication required")

    row, _ = found
    return AuthUser(
        id=row["id"],
        username=row["username"],
        role=row["role"],
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        last_login_at=row["last_login_at"],
    )


def require_parent(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.role != "parent":
        raise HTTPException(status_code=403, detail="parent role required")
    return user


class BootstrapRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: Literal["parent", "child"] = "child"


class ActiveRequest(BaseModel):
    is_active: bool


class ResetPasswordRequest(BaseModel):
    password: str


@router.get("/bootstrap-status")
def bootstrap_status():
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    return {"needs_bootstrap": count == 0}


@router.post("/bootstrap", status_code=201)
def bootstrap(payload: BootstrapRequest, response: Response):
    with connect() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            if count != 0:
                raise HTTPException(status_code=409, detail="bootstrap already completed")

            user = _create_user(
                conn,
                username=payload.username,
                password=payload.password,
                role="parent",
            )
            token, expires = _create_session(conn, user["id"])
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise

    _set_session_cookie(response, token, expires)
    return {"user": _public_user(user)}


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    try:
        password = normalize_password(payload.password, enforce_minimum=False)
    except ValueError as exc:
        raise _http_422(str(exc)) from exc

    try:
        username = normalize_username(payload.username)
    except ValueError:
        # Still perform Argon2 work before returning the generic failure.
        verify_password(password, DUMMY_PASSWORD_HASH)
        raise HTTPException(status_code=401, detail="invalid credentials")

    with connect() as conn:
        user = _fetch_user_by_username(conn, username)
        candidate_hash = user["password_hash"] if user else DUMMY_PASSWORD_HASH
        valid = verify_password(password, candidate_hash)

        if user is None or not valid or not bool(user["is_active"]):
            raise HTTPException(status_code=401, detail="invalid credentials")

        try:
            conn.execute("BEGIN IMMEDIATE")
            # Re-read after acquiring the write lock in case the account was disabled.
            user = _fetch_user_by_id(conn, user["id"])
            if user is None or not bool(user["is_active"]):
                raise HTTPException(status_code=401, detail="invalid credentials")
            token, expires = _create_session(conn, user["id"])
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise

    _set_session_cookie(response, token, expires)
    return {"user": _public_user(user)}


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        with connect() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET revoked_at = ?
                WHERE token_hash = ? AND revoked_at IS NULL
                """,
                (utc_text(), hash_session_token(token)),
            )
    _clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
def me(user: AuthUser = Depends(get_current_user)):
    return {"user": _public_user(user)}


@router.get("/users")
def list_users(_: AuthUser = Depends(require_parent)):
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, username, role, is_active,
                   created_at, updated_at, last_login_at
            FROM users
            ORDER BY created_at, username
            """
        ).fetchall()
    return {"users": [_public_user(row) for row in rows]}


@router.post("/users", status_code=201)
def create_user(
    payload: CreateUserRequest,
    _: AuthUser = Depends(require_parent),
):
    with connect() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            user = _create_user(
                conn,
                username=payload.username,
                password=payload.password,
                role=payload.role,
            )
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise
    return {"user": _public_user(user)}


@router.patch("/users/{user_id}/active")
def set_user_active(
    user_id: str,
    payload: ActiveRequest,
    _: AuthUser = Depends(require_parent),
):
    with connect() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            target = _fetch_user_by_id(conn, user_id)
            if target is None:
                raise HTTPException(status_code=404, detail="user not found")

            if not payload.is_active and target["role"] == "parent" and bool(target["is_active"]):
                active_parents = conn.execute(
                    "SELECT COUNT(*) FROM users WHERE role = 'parent' AND is_active = 1"
                ).fetchone()[0]
                if active_parents <= 1:
                    raise HTTPException(
                        status_code=409,
                        detail="cannot disable the last active parent",
                    )

            now = utc_text()
            conn.execute(
                "UPDATE users SET is_active = ?, updated_at = ? WHERE id = ?",
                (1 if payload.is_active else 0, now, user_id),
            )
            if not payload.is_active:
                conn.execute(
                    """
                    UPDATE sessions
                    SET revoked_at = ?
                    WHERE user_id = ? AND revoked_at IS NULL
                    """,
                    (now, user_id),
                )
            updated = _fetch_user_by_id(conn, user_id)
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise

    return {"user": _public_user(updated)}


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: str,
    payload: ResetPasswordRequest,
    _: AuthUser = Depends(require_parent),
):
    try:
        new_hash = hash_password(payload.password)
    except ValueError as exc:
        raise _http_422(str(exc)) from exc

    with connect() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            target = _fetch_user_by_id(conn, user_id)
            if target is None:
                raise HTTPException(status_code=404, detail="user not found")

            now = utc_text()
            conn.execute(
                """
                UPDATE users
                SET password_hash = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_hash, now, user_id),
            )
            conn.execute(
                """
                UPDATE sessions
                SET revoked_at = ?
                WHERE user_id = ? AND revoked_at IS NULL
                """,
                (now, user_id),
            )
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise

    return {"ok": True}
