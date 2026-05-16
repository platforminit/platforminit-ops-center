"""Testable scheduler service for running due registered checks.

This module provides pure functions to determine which registered checks
are due for execution based on their ``interval_seconds`` and the last
recorded run time, and a service function that runs all due checks and
persists their results.

The module does **not** start any background loop — it is designed to be
called from an API endpoint, a CLI command, or a future scheduler loop.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.runner.models import PluginResult
from app.runner.nagios import run_nagios_plugin
from app.store.check_results import (
    CheckResultRecord,
    get_latest_results,
    persist_check_result,
)


def _parse_iso_timestamp(ts: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp string, or return *None* for empty input."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def is_check_due(
    interval_seconds: int,
    last_run_at: datetime | None,
    *,
    now: datetime | None = None,
) -> bool:
    """Determine whether a check is due to run.

    Parameters
    ----------
    interval_seconds:
        The check's configured interval in seconds.
    last_run_at:
        The datetime of the last successful run, or *None* if the check
        has never been run.
    now:
        The current datetime (injected for testability). Defaults to
        ``datetime.now(timezone.utc)``.

    Returns
    -------
    ``True`` if the check is due, ``False`` otherwise.
    """
    if interval_seconds < 0:
        return False

    if last_run_at is None:
        # Never run → due immediately.
        return True

    reference = now if now is not None else datetime.now(timezone.utc)
    elapsed = (reference - last_run_at).total_seconds()
    return elapsed >= interval_seconds


def get_due_check_ids(
    *,
    now: datetime | None = None,
) -> list[str]:
    """Return the list of registered check IDs that are due for execution.

    Parameters
    ----------
    now:
        Injected timestamp for testability.

    Returns
    -------
    A list of check IDs that are due, sorted alphabetically.
    """
    # Lazy import to avoid circular dependency: app.api.checks imports
    # from this module, so we cannot import from app.api.checks at the
    # module level.
    from app.api.checks import get_registered_checks  # fmt: skip

    reference = now if now is not None else datetime.now(timezone.utc)
    registry = get_registered_checks()
    check_ids = sorted(registry.keys())

    if not check_ids:
        return []

    latest_records = get_latest_results(check_ids)
    latest_by_check_id: dict[str, CheckResultRecord] = {
        record.check_id: record for record in latest_records
    }

    due: list[str] = []
    for check_id in check_ids:
        metadata = registry[check_id]
        record = latest_by_check_id.get(check_id)
        last_run_at = (
            _parse_iso_timestamp(record.created_at) if record else None
        )

        if is_check_due(metadata.interval_seconds, last_run_at, now=reference):
            due.append(check_id)

    return due


def run_due_checks(
    *,
    now: datetime | None = None,
    timeout_seconds: int = 10,
) -> list[tuple[str, PluginResult]]:
    """Run all due registered checks and persist their results.

    Parameters
    ----------
    now:
        Injected timestamp for testability.
    timeout_seconds:
        Timeout passed to each plugin execution.

    Returns
    -------
    A list of ``(check_id, PluginResult)`` tuples for every check that
    was executed, in the order they were run.
    """
    # Lazy import to avoid circular dependency.
    from app.api.checks import get_registered_command  # fmt: skip

    due_ids = get_due_check_ids(now=now)
    results: list[tuple[str, PluginResult]] = []

    for check_id in due_ids:
        command = get_registered_command(check_id)
        if command is None:
            # Should not happen for registered checks, but guard anyway.
            continue

        result = run_nagios_plugin(
            command=command,
            timeout_seconds=timeout_seconds,
        )
        persist_check_result(check_id, result)
        results.append((check_id, result))

    return results
