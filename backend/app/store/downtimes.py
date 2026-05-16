from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.store.database import create_connection, initialize_schema


def _utc_iso(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class DowntimeRecord:
    id: int
    check_id: str
    start_time: str
    end_time: str
    reason: str
    operator: str
    created_at: str


def _row_to_record(row) -> DowntimeRecord:
    return DowntimeRecord(
        id=int(row["id"]),
        check_id=str(row["check_id"]),
        start_time=str(row["start_time"]),
        end_time=str(row["end_time"]),
        reason=str(row["reason"]),
        operator=str(row["operator"]),
        created_at=str(row["created_at"]),
    )


def persist_downtime(
    check_id: str,
    start_time: str,
    end_time: str,
    reason: str,
    operator: str,
) -> DowntimeRecord:
    start_time = _utc_iso(start_time)
    end_time = _utc_iso(end_time)
    created_at = datetime.now(timezone.utc).isoformat()

    with create_connection() as connection:
        initialize_schema(connection)
        cursor = connection.execute(
            """
            INSERT INTO downtimes (check_id, start_time, end_time, reason, operator, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (check_id, start_time, end_time, reason, operator, created_at),
        )
        connection.commit()

        row = connection.execute(
            "SELECT * FROM downtimes WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    if row is None:
        raise RuntimeError("persisted downtime could not be loaded")

    return _row_to_record(row)


def get_downtimes(check_id: str) -> list[DowntimeRecord]:
    """Return all downtimes for a check, ordered by start_time descending."""
    with create_connection() as connection:
        initialize_schema(connection)
        rows = connection.execute(
            """
            SELECT *
            FROM downtimes
            WHERE check_id = ?
            ORDER BY start_time DESC, id DESC
            """,
            (check_id,),
        ).fetchall()

    return [_row_to_record(row) for row in rows]


def is_check_in_downtime(check_id: str, reference_time: str | None = None) -> bool:
    """Return True if the check has an active downtime window covering *reference_time*.

    If *reference_time* is None, the current UTC time is used.
    """
    if reference_time is None:
        reference_time = datetime.now(timezone.utc).isoformat()
    else:
        reference_time = _utc_iso(reference_time)

    with create_connection() as connection:
        initialize_schema(connection)
        row = connection.execute(
            """
            SELECT 1
            FROM downtimes
            WHERE check_id = ?
              AND start_time <= ?
              AND end_time >= ?
            LIMIT 1
            """,
            (check_id, reference_time, reference_time),
        ).fetchone()

    return row is not None


def get_downtime_map(
    check_ids: list[str],
    reference_time: str | None = None,
) -> dict[str, bool]:
    """Return a dict mapping check_id -> bool indicating active downtime."""
    if not check_ids:
        return {}

    if reference_time is None:
        reference_time = datetime.now(timezone.utc).isoformat()
    else:
        reference_time = _utc_iso(reference_time)

    placeholders = ", ".join("?" for _ in check_ids)
    query = f"""
        SELECT DISTINCT check_id
        FROM downtimes
        WHERE check_id IN ({placeholders})
          AND start_time <= ?
          AND end_time >= ?
    """

    with create_connection() as connection:
        initialize_schema(connection)
        rows = connection.execute(
            query,
            (*check_ids, reference_time, reference_time),
        ).fetchall()

    in_downtime = {str(row["check_id"]): True for row in rows}
    return {check_id: in_downtime.get(check_id, False) for check_id in check_ids}
