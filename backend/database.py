import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


MIGRATIONS_DIR = Path(__file__).with_name("migrations")


def db_path() -> str:
    data_dir = os.environ.get("QUESTBOARD_DATA", "/data")
    return os.environ.get(
        "QUESTBOARD_DB",
        os.path.join(data_dir, "questboard.db"),
    )


@contextmanager
def connect(path: str | None = None) -> Iterator[sqlite3.Connection]:
    target = path or db_path()

    conn = sqlite3.connect(
        target,
        timeout=5.0,
        isolation_level=None,
    )
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
        yield conn
    finally:
        conn.close()


def _ensure_migration_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (
                strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            )
        )
        """
    )


def _migration_applied(
    conn: sqlite3.Connection,
    filename: str,
) -> bool:
    row = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE filename = ?",
        (filename,),
    ).fetchone()

    return row is not None


def _apply_migration(
    conn: sqlite3.Connection,
    path: Path,
) -> None:
    sql = path.read_text(encoding="utf-8")

    # Migration filenames are repository-controlled, but still escape
    # single quotes before embedding the value in executescript().
    migration_name = path.name.replace("'", "''")

    script = f"""
BEGIN IMMEDIATE;

{sql}

INSERT INTO schema_migrations (filename)
VALUES ('{migration_name}');

COMMIT;
"""

    try:
        conn.executescript(script)
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise


def initialize_database(path: str | None = None) -> None:
    target = path or db_path()

    parent = os.path.dirname(target)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with connect(target) as conn:
        _ensure_migration_table(conn)

        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if not _migration_applied(conn, migration.name):
                _apply_migration(conn, migration)
