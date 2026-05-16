"""Shared SQLite database initialization for the PlatformInit Ops Center.

Centralises path resolution, connection creation, and schema initialisation
so that all store modules use a single source of truth.  This makes the
initialisation path predictable and test-friendly — tests can point the
DB at a temporary path without worrying about global side effects.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.core.config import load_settings


def get_database_path() -> Path:
    """Return the configured or default SQLite database path.

    Respects the ``PLATFORMINIT_CHECK_RESULTS_DB`` environment variable.
    Falls back to ``<project-root>/check_results.sqlite3``.
    """
    configured = load_settings().check_results_db
    if configured is not None:
        return configured

    return Path(__file__).resolve().parents[2] / "check_results.sqlite3"


def create_connection() -> sqlite3.Connection:
    """Open a connection to the SQLite database, creating parent dirs if needed.

    Returns a connection with ``row_factory`` set to ``sqlite3.Row``.
    """
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


# ---------------------------------------------------------------------------
# Schema DDL  (tables and indexes)
# ---------------------------------------------------------------------------

_SCHEMA_STATEMENTS: list[str] = [
    # check_results
    """
    CREATE TABLE IF NOT EXISTS check_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        check_id TEXT NOT NULL,
        status TEXT NOT NULL,
        output TEXT NOT NULL,
        perfdata TEXT,
        stderr TEXT,
        exit_code INTEGER NOT NULL,
        duration_seconds REAL NOT NULL,
        timed_out INTEGER NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_check_results_check_id_created_at
    ON check_results (check_id, created_at DESC, id DESC)
    """,
    # acknowledgements
    """
    CREATE TABLE IF NOT EXISTS acknowledgements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        check_id TEXT NOT NULL,
        operator TEXT NOT NULL,
        reason TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_acknowledgements_check_id
    ON acknowledgements (check_id, created_at DESC)
    """,
    # comments
    """
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        check_id TEXT NOT NULL,
        operator TEXT NOT NULL,
        comment TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_comments_check_id
    ON comments (check_id, created_at DESC)
    """,
    # downtimes
    """
    CREATE TABLE IF NOT EXISTS downtimes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        check_id TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        reason TEXT NOT NULL,
        operator TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_downtimes_check_id
    ON downtimes (check_id, start_time DESC)
    """,
    # hosts
    """
    CREATE TABLE IF NOT EXISTS hosts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        environment TEXT NOT NULL,
        criticality TEXT NOT NULL,
        owner TEXT NOT NULL,
        runbook_url TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_hosts_name
    ON hosts (name)
    """,
    # services
    """
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        host_id INTEGER NOT NULL,
        environment TEXT NOT NULL,
        criticality TEXT NOT NULL,
        owner TEXT NOT NULL,
        runbook_url TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (host_id) REFERENCES hosts(id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_services_name
    ON services (name)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_services_host_id
    ON services (host_id)
    """,
]


def initialize_schema(connection: sqlite3.Connection) -> None:
    """Create all tables and indexes if they do not already exist.

    Idempotent — safe to call repeatedly.
    """
    for statement in _SCHEMA_STATEMENTS:
        connection.execute(statement)
    connection.commit()
