ALTER TABLE users ADD COLUMN last_login_at TEXT;

CREATE INDEX IF NOT EXISTS idx_users_role_active
    ON users(role, is_active);

CREATE INDEX IF NOT EXISTS idx_sessions_user_validity
    ON sessions(user_id, revoked_at, expires_at);
