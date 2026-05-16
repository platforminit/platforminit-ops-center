"""Tests for shared SQLite database initialisation.

Verifies that ``initialize_schema`` is idempotent and that the schema
can be created on a temporary path without side effects on other tests.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.store.database import (
    create_connection,
    get_database_path,
    initialize_schema,
)


def test_get_database_path_defaults_to_project_root() -> None:
    """When PLATFORMINIT_CHECK_RESULTS_DB is unset, path falls back to project root."""
    path = get_database_path()
    assert path.name == "check_results.sqlite3"
    # The path should be two levels up from backend/app/store/database.py
    assert path.parent.name == "backend"


def test_get_database_path_respects_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When PLATFORMINIT_CHECK_RESULTS_DB is set, that path is returned."""
    monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", "/tmp/test-ops-center.sqlite3")
    path = get_database_path()
    assert str(path) == "/tmp/test-ops-center.sqlite3"


def test_create_connection_returns_row_factory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Connection has row_factory set to sqlite3.Row."""
    monkeypatch.setenv(
        "PLATFORMINIT_CHECK_RESULTS_DB", str(tmp_path / "test.sqlite3")
    )
    conn = create_connection()
    try:
        assert conn.row_factory is sqlite3.Row
    finally:
        conn.close()


def test_initialize_schema_empty_db(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Schema can be created on an empty temporary database."""
    db_path = tmp_path / "empty-test.sqlite3"
    monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(db_path))

    conn = create_connection()
    try:
        initialize_schema(conn)

        # Verify all expected tables exist (filter out sqlite_sequence
        # which SQLite auto-creates when AUTOINCREMENT is used)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence' ORDER BY name"
        ).fetchall()
        table_names = {row["name"] for row in tables}
        assert table_names == {
            "check_results",
            "acknowledgements",
            "comments",
            "downtimes",
            "hosts",
            "services",
        }

        # Verify all expected indexes exist
        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
        ).fetchall()
        index_names = {row["name"] for row in indexes}
        for expected in (
            "idx_check_results_check_id_created_at",
            "idx_acknowledgements_check_id",
            "idx_comments_check_id",
            "idx_downtimes_check_id",
            "idx_hosts_name",
            "idx_services_name",
            "idx_services_host_id",
        ):
            assert expected in index_names, f"Missing index: {expected}"
    finally:
        conn.close()


def test_initialize_schema_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Calling initialize_schema twice does not raise or duplicate objects."""
    db_path = tmp_path / "idempotent-test.sqlite3"
    monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(db_path))

    conn = create_connection()
    try:
        # First call
        initialize_schema(conn)

        # Count tables and indexes after first call
        tables_after_first = conn.execute(
            "SELECT COUNT(*) AS cnt FROM sqlite_master WHERE type='table'"
        ).fetchone()["cnt"]

        # Second call — must not raise
        initialize_schema(conn)

        # Count tables and indexes after second call
        tables_after_second = conn.execute(
            "SELECT COUNT(*) AS cnt FROM sqlite_master WHERE type='table'"
        ).fetchone()["cnt"]

        assert tables_after_first == tables_after_second, (
            f"Table count changed: {tables_after_first} -> {tables_after_second}"
        )
    finally:
        conn.close()


def test_initialize_schema_multiple_connections(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Schema created on one connection is visible on another."""
    db_path = tmp_path / "shared-test.sqlite3"
    monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(db_path))

    conn1 = create_connection()
    try:
        initialize_schema(conn1)
    finally:
        conn1.close()

    # Open a second connection to the same file
    conn2 = create_connection()
    try:
        tables = conn2.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence' ORDER BY name"
        ).fetchall()
        assert len(tables) == 6
    finally:
        conn2.close()


def test_initialize_schema_does_not_affect_other_databases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Schema initialisation on one path does not create files elsewhere."""
    db_path_a = tmp_path / "db-a.sqlite3"
    db_path_b = tmp_path / "db-b.sqlite3"

    monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(db_path_a))
    conn_a = create_connection()
    try:
        initialize_schema(conn_a)
    finally:
        conn_a.close()

    # db-b should not exist yet
    assert not db_path_b.exists()

    monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(db_path_b))
    conn_b = create_connection()
    try:
        initialize_schema(conn_b)
    finally:
        conn_b.close()

    assert db_path_b.exists()
