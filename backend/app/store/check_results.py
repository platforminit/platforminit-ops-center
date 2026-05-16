from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.runner.models import PluginResult


DEFAULT_HISTORY_LIMIT = 25
MAX_HISTORY_LIMIT = 100


@dataclass(frozen=True)
class CheckResultRecord:
    id: int
    check_id: str
    status: str
    output: str
    perfdata: str | None
    stderr: str | None
    exit_code: int
    duration_seconds: float
    timed_out: bool
    created_at: str


def _database_path() -> Path:
    configured_path = os.environ.get("PLATFORMINIT_CHECK_RESULTS_DB")
    if configured_path:
        return Path(configured_path)

    return Path(__file__).resolve().parents[2] / "check_results.sqlite3"


def _connect() -> sqlite3.Connection:
    database_path = _database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
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
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_check_results_check_id_created_at
        ON check_results (check_id, created_at DESC, id DESC)
        """
    )
    connection.commit()


def _row_to_record(row: sqlite3.Row) -> CheckResultRecord:
    return CheckResultRecord(
        id=int(row["id"]),
        check_id=str(row["check_id"]),
        status=str(row["status"]),
        output=str(row["output"]),
        perfdata=row["perfdata"],
        stderr=row["stderr"],
        exit_code=int(row["exit_code"]),
        duration_seconds=float(row["duration_seconds"]),
        timed_out=bool(row["timed_out"]),
        created_at=str(row["created_at"]),
    )


def persist_check_result(check_id: str, result: PluginResult) -> CheckResultRecord:
    created_at = datetime.now(timezone.utc).isoformat()

    with _connect() as connection:
        _ensure_schema(connection)
        cursor = connection.execute(
            """
            INSERT INTO check_results (
                check_id,
                status,
                output,
                perfdata,
                stderr,
                exit_code,
                duration_seconds,
                timed_out,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                check_id,
                result.status.value,
                result.output,
                result.perfdata,
                result.stderr,
                result.exit_code,
                result.duration_seconds,
                1 if result.timed_out else 0,
                created_at,
            ),
        )
        connection.commit()

        row = connection.execute(
            "SELECT * FROM check_results WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    if row is None:
        raise RuntimeError("persisted check result could not be loaded")

    return _row_to_record(row)


def get_check_history(check_id: str, limit: int = DEFAULT_HISTORY_LIMIT) -> list[CheckResultRecord]:
    normalized_limit = min(max(limit, 1), MAX_HISTORY_LIMIT)

    with _connect() as connection:
        _ensure_schema(connection)
        rows = connection.execute(
            """
            SELECT *
            FROM check_results
            WHERE check_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (check_id, normalized_limit),
        ).fetchall()

    return [_row_to_record(row) for row in rows]


def get_latest_results(check_ids: list[str]) -> list[CheckResultRecord]:
    if not check_ids:
        return []

    placeholders = ", ".join("?" for _ in check_ids)
    query = f"""
        SELECT cr.*
        FROM check_results AS cr
        INNER JOIN (
            SELECT check_id, MAX(id) AS id
            FROM check_results
            WHERE check_id IN ({placeholders})
            GROUP BY check_id
        ) AS latest
            ON cr.check_id = latest.check_id
            AND cr.id = latest.id
        ORDER BY cr.check_id ASC
    """

    with _connect() as connection:
        _ensure_schema(connection)
        rows = connection.execute(query, tuple(check_ids)).fetchall()

    return [_row_to_record(row) for row in rows]


_SEVERITY_ORDER = {"CRITICAL": 0, "WARNING": 1, "UNKNOWN": 2}


def get_problems(check_ids: list[str]) -> list[CheckResultRecord]:
    """Return the latest result for each registered check whose status is
    WARNING, CRITICAL, or UNKNOWN, sorted by severity (CRITICAL first)
    then newest first."""
    if not check_ids:
        return []

    placeholders = ", ".join("?" for _ in check_ids)
    query = f"""
        SELECT cr.*
        FROM check_results AS cr
        INNER JOIN (
            SELECT check_id, MAX(id) AS id
            FROM check_results
            WHERE check_id IN ({placeholders})
            GROUP BY check_id
        ) AS latest
            ON cr.check_id = latest.check_id
            AND cr.id = latest.id
        WHERE cr.status IN ('WARNING', 'CRITICAL', 'UNKNOWN')
    """

    with _connect() as connection:
        _ensure_schema(connection)
        rows = connection.execute(query, tuple(check_ids)).fetchall()

    records = [_row_to_record(row) for row in rows]
    records.sort(
        key=lambda r: (
            _SEVERITY_ORDER.get(r.status, 99),
            r.created_at or "",
        )
    )
    return records

