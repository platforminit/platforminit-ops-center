"""Inventory store — host and service metadata persisted in SQLite."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from app.store.database import create_connection, initialize_schema


# ---------------------------------------------------------------------------
# Data records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HostRecord:
    id: int
    name: str
    environment: str
    criticality: str
    owner: str
    runbook_url: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ServiceRecord:
    id: int
    name: str
    host_id: int
    environment: str
    criticality: str
    owner: str
    runbook_url: str
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Row mapping helpers
# ---------------------------------------------------------------------------


def _host_row_to_record(row: sqlite3.Row) -> HostRecord:
    return HostRecord(
        id=int(row["id"]),
        name=str(row["name"]),
        environment=str(row["environment"]),
        criticality=str(row["criticality"]),
        owner=str(row["owner"]),
        runbook_url=str(row["runbook_url"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _service_row_to_record(row: sqlite3.Row) -> ServiceRecord:
    return ServiceRecord(
        id=int(row["id"]),
        name=str(row["name"]),
        host_id=int(row["host_id"]),
        environment=str(row["environment"]),
        criticality=str(row["criticality"]),
        owner=str(row["owner"]),
        runbook_url=str(row["runbook_url"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


# ---------------------------------------------------------------------------
# Seed data — initial hosts and services for MVP
# ---------------------------------------------------------------------------


_SEED_HOSTS: list[dict[str, str]] = [
    {
        "name": "web-01",
        "environment": "production",
        "criticality": "high",
        "owner": "platform-team",
        "runbook_url": "https://example.com/runbooks/web-01",
    },
    {
        "name": "db-01",
        "environment": "production",
        "criticality": "high",
        "owner": "platform-team",
        "runbook_url": "https://example.com/runbooks/db-01",
    },
    {
        "name": "cache-01",
        "environment": "staging",
        "criticality": "medium",
        "owner": "platform-team",
        "runbook_url": "https://example.com/runbooks/cache-01",
    },
]

_SEED_SERVICES: list[dict[str, str | int]] = [
    {
        "name": "http-check",
        "host_id": 1,
        "environment": "production",
        "criticality": "high",
        "owner": "platform-team",
        "runbook_url": "https://example.com/runbooks/http-check",
    },
    {
        "name": "postgres-health",
        "host_id": 2,
        "environment": "production",
        "criticality": "high",
        "owner": "dba-team",
        "runbook_url": "https://example.com/runbooks/postgres-health",
    },
    {
        "name": "redis-health",
        "host_id": 3,
        "environment": "staging",
        "criticality": "medium",
        "owner": "platform-team",
        "runbook_url": "https://example.com/runbooks/redis-health",
    },
]


def _seed(connection: sqlite3.Connection) -> None:
    """Insert seed data if the hosts table is empty."""
    existing = connection.execute("SELECT COUNT(*) AS cnt FROM hosts").fetchone()
    if existing and int(existing["cnt"]) > 0:
        return

    now = datetime.now(timezone.utc).isoformat()
    for host in _SEED_HOSTS:
        connection.execute(
            """
            INSERT OR IGNORE INTO hosts (name, environment, criticality, owner, runbook_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                host["name"],
                host["environment"],
                host["criticality"],
                host["owner"],
                host["runbook_url"],
                now,
                now,
            ),
        )

    for service in _SEED_SERVICES:
        connection.execute(
            """
            INSERT OR IGNORE INTO services (name, host_id, environment, criticality, owner, runbook_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                service["name"],
                service["host_id"],
                service["environment"],
                service["criticality"],
                service["owner"],
                service["runbook_url"],
                now,
                now,
            ),
        )

    connection.commit()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_hosts() -> list[HostRecord]:
    """Return all hosts ordered by name."""
    with create_connection() as connection:
        initialize_schema(connection)
        _seed(connection)
        rows = connection.execute(
            "SELECT * FROM hosts ORDER BY name ASC"
        ).fetchall()

    return [_host_row_to_record(row) for row in rows]


def list_services() -> list[ServiceRecord]:
    """Return all services ordered by name."""
    with create_connection() as connection:
        initialize_schema(connection)
        _seed(connection)
        rows = connection.execute(
            "SELECT * FROM services ORDER BY name ASC"
        ).fetchall()

    return [_service_row_to_record(row) for row in rows]
