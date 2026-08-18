CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    role TEXT NOT NULL DEFAULT 'user',
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),
    updated_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    )
);


CREATE TABLE IF NOT EXISTS players (
    id TEXT PRIMARY KEY,
    user_id TEXT UNIQUE,
    questboard_player_id TEXT UNIQUE,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),
    updated_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE SET NULL
);


CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),
    last_seen_at TEXT,
    revoked_at TEXT,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id
    ON sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_sessions_expires_at
    ON sessions(expires_at);


CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    )
);


CREATE TABLE IF NOT EXISTS state_snapshots (
    id TEXT PRIMARY KEY,
    snapshot_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    source_version TEXT,
    created_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    )
);

CREATE INDEX IF NOT EXISTS idx_state_snapshots_created_at
    ON state_snapshots(created_at);


CREATE TABLE IF NOT EXISTS gold_accounts (
    id TEXT PRIMARY KEY,

    -- System holdings use explicit identities too:
    -- e.g. owner_type='system', owner_id='kingdom-vault'.
    owner_type TEXT NOT NULL,
    owner_id TEXT NOT NULL,

    account_type TEXT NOT NULL,
    label TEXT,

    is_active INTEGER NOT NULL DEFAULT 1
        CHECK (is_active IN (0, 1)),

    created_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),
    updated_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),

    UNIQUE (owner_type, owner_id, account_type)
);

CREATE INDEX IF NOT EXISTS idx_gold_accounts_owner
    ON gold_accounts(owner_type, owner_id);


CREATE TABLE IF NOT EXISTS gold_ledger (
    id TEXT PRIMARY KEY,

    -- Gold quantities are represented as positive integers.
    -- Direction is represented by source/destination accounts.
    amount INTEGER NOT NULL
        CHECK (amount > 0),

    source_account_id TEXT,
    destination_account_id TEXT,

    category TEXT NOT NULL,
    reason TEXT NOT NULL,

    actor_type TEXT,
    actor_id TEXT,

    related_entity_type TEXT,
    related_entity_id TEXT,

    correction_of_ledger_id TEXT,

    created_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),

    CHECK (
        source_account_id IS NOT NULL
        OR destination_account_id IS NOT NULL
    ),

    CHECK (
        source_account_id IS NULL
        OR destination_account_id IS NULL
        OR source_account_id <> destination_account_id
    ),

    CHECK (
        correction_of_ledger_id IS NULL
        OR correction_of_ledger_id <> id
    ),

    FOREIGN KEY (source_account_id)
        REFERENCES gold_accounts(id),

    FOREIGN KEY (destination_account_id)
        REFERENCES gold_accounts(id),

    FOREIGN KEY (correction_of_ledger_id)
        REFERENCES gold_ledger(id)
);

CREATE INDEX IF NOT EXISTS idx_gold_ledger_source
    ON gold_ledger(source_account_id);

CREATE INDEX IF NOT EXISTS idx_gold_ledger_destination
    ON gold_ledger(destination_account_id);

CREATE INDEX IF NOT EXISTS idx_gold_ledger_category
    ON gold_ledger(category);

CREATE INDEX IF NOT EXISTS idx_gold_ledger_created_at
    ON gold_ledger(created_at);

CREATE INDEX IF NOT EXISTS idx_gold_ledger_correction
    ON gold_ledger(correction_of_ledger_id);


CREATE TRIGGER IF NOT EXISTS gold_ledger_no_update
BEFORE UPDATE ON gold_ledger
BEGIN
    SELECT RAISE(
        ABORT,
        'gold_ledger is append-only'
    );
END;


CREATE TRIGGER IF NOT EXISTS gold_ledger_no_delete
BEFORE DELETE ON gold_ledger
BEGIN
    SELECT RAISE(
        ABORT,
        'gold_ledger is append-only'
    );
END;


CREATE TABLE IF NOT EXISTS royal_mail (
    id TEXT PRIMARY KEY,

    recipient_type TEXT NOT NULL,
    recipient_id TEXT NOT NULL,

    sender_type TEXT,
    sender_id TEXT,

    message_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,

    is_read INTEGER NOT NULL DEFAULT 0
        CHECK (is_read IN (0, 1)),

    read_at TEXT,

    related_entity_type TEXT,
    related_entity_id TEXT,

    created_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    )
);

CREATE INDEX IF NOT EXISTS idx_royal_mail_recipient
    ON royal_mail(recipient_type, recipient_id);

CREATE INDEX IF NOT EXISTS idx_royal_mail_unread
    ON royal_mail(recipient_type, recipient_id, is_read);

CREATE INDEX IF NOT EXISTS idx_royal_mail_created_at
    ON royal_mail(created_at);
