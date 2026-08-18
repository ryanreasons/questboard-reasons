import sqlite3

import pytest

from backend.database import connect, initialize_database


EXPECTED_TABLES = {
    "schema_migrations",
    "users",
    "players",
    "sessions",
    "app_settings",
    "state_snapshots",
    "gold_accounts",
    "gold_ledger",
    "royal_mail",
}


def test_initialize_creates_schema_and_records_migration(tmp_path, monkeypatch):
    db_path = tmp_path / "questboard.db"
    monkeypatch.setenv("QUESTBOARD_DB", str(db_path))

    initialize_database()

    assert db_path.exists()

    with connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

        assert EXPECTED_TABLES <= tables

        migrations = [
            row[0]
            for row in conn.execute(
                "SELECT filename FROM schema_migrations ORDER BY filename"
            )
        ]

        assert migrations == ["001_initial.sql", "002_auth.sql"]
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_initialize_is_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "questboard.db"
    monkeypatch.setenv("QUESTBOARD_DB", str(db_path))

    initialize_database()
    initialize_database()

    with connect() as conn:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM schema_migrations"
            ).fetchone()[0]
            == 2
        )

        assert conn.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0] == 0


def test_reopen_preserves_schema_state(tmp_path, monkeypatch):
    db_path = tmp_path / "questboard.db"
    monkeypatch.setenv("QUESTBOARD_DB", str(db_path))

    initialize_database()

    with connect() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?)",
            ("sample", "value"),
        )

    initialize_database()

    with connect() as conn:
        assert conn.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            ("sample",),
        ).fetchone()[0] == "value"

        assert (
            conn.execute(
                "SELECT COUNT(*) FROM schema_migrations"
            ).fetchone()[0]
            == 2
        )


def test_gold_ledger_is_append_only(tmp_path, monkeypatch):
    db_path = tmp_path / "questboard.db"
    monkeypatch.setenv("QUESTBOARD_DB", str(db_path))

    initialize_database()

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO gold_accounts (
                id,
                owner_type,
                owner_id,
                account_type
            )
            VALUES (?, ?, ?, ?)
            """,
            ("acct-1", "player", "player-1", "wallet"),
        )

        conn.execute(
            """
            INSERT INTO gold_ledger (
                id,
                amount,
                source_account_id,
                destination_account_id,
                category,
                reason
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "led-1",
                10,
                None,
                "acct-1",
                "test",
                "seed",
            ),
        )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE gold_ledger "
                "SET amount = 20 "
                "WHERE id = 'led-1'"
            )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "DELETE FROM gold_ledger WHERE id = 'led-1'"
            )


def test_gold_ledger_rejects_invalid_transactions(tmp_path, monkeypatch):
    db_path = tmp_path / "questboard.db"
    monkeypatch.setenv("QUESTBOARD_DB", str(db_path))

    initialize_database()

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO gold_accounts (
                id,
                owner_type,
                owner_id,
                account_type
            )
            VALUES (?, ?, ?, ?)
            """,
            ("acct-1", "player", "player-1", "wallet"),
        )

        # Gold quantities must always be positive.
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO gold_ledger (
                    id,
                    amount,
                    destination_account_id,
                    category,
                    reason
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                ("bad-zero", 0, "acct-1", "test", "invalid"),
            )

        # A ledger entry must have a source or destination.
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO gold_ledger (
                    id,
                    amount,
                    category,
                    reason
                )
                VALUES (?, ?, ?, ?)
                """,
                ("bad-nowhere", 10, "test", "invalid"),
            )

        # Moving Gold from an account to itself is invalid.
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO gold_ledger (
                    id,
                    amount,
                    source_account_id,
                    destination_account_id,
                    category,
                    reason
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "bad-self-transfer",
                    10,
                    "acct-1",
                    "acct-1",
                    "test",
                    "invalid",
                ),
            )


def test_gold_account_identity_is_unique(tmp_path, monkeypatch):
    db_path = tmp_path / "questboard.db"
    monkeypatch.setenv("QUESTBOARD_DB", str(db_path))

    initialize_database()

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO gold_accounts (
                id,
                owner_type,
                owner_id,
                account_type
            )
            VALUES (?, ?, ?, ?)
            """,
            ("acct-1", "player", "player-1", "wallet"),
        )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO gold_accounts (
                    id,
                    owner_type,
                    owner_id,
                    account_type
                )
                VALUES (?, ?, ?, ?)
                """,
                ("acct-2", "player", "player-1", "wallet"),
            )


def test_failed_migration_rolls_back_only_failed_migration(
    tmp_path,
    monkeypatch,
):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    (migrations_dir / "001_ok.sql").write_text(
        "CREATE TABLE ok(id TEXT PRIMARY KEY);",
        encoding="utf-8",
    )

    (migrations_dir / "002_fail.sql").write_text(
        (
            "CREATE TABLE broken(id TEXT PRIMARY KEY);\n"
            "INSERT INTO missing_table VALUES (1);"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "backend.database.MIGRATIONS_DIR",
        migrations_dir,
    )

    db_path = tmp_path / "questboard.db"
    monkeypatch.setenv("QUESTBOARD_DB", str(db_path))

    with pytest.raises(sqlite3.OperationalError):
        initialize_database()

    with connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

        assert "schema_migrations" in tables

        # Migration 001 committed successfully.
        assert "ok" in tables

        # Migration 002 must leave no partial schema.
        assert "broken" not in tables

        applied = [
            row[0]
            for row in conn.execute(
                "SELECT filename "
                "FROM schema_migrations "
                "ORDER BY filename"
            )
        ]

        assert applied == ["001_ok.sql"]


def test_database_supports_relative_filename(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    initialize_database("questboard.db")

    assert (tmp_path / "questboard.db").exists()

    with connect("questboard.db") as conn:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM schema_migrations"
            ).fetchone()[0]
            == 2
        )
