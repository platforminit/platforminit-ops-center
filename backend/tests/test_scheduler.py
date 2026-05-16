"""Tests for the scheduler service module.

Covers:
- ``is_check_due``: due/not-due logic, never-run logic, edge cases.
- ``get_due_check_ids``: integration with registry and store.
- ``run_due_checks``: one scheduler execution with mocked plugin runner.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.runner.models import CheckStatus, PluginResult
from app.scheduler.service import (
    get_due_check_ids,
    is_check_due,
    run_due_checks,
)


def _fake_result(
    command: list[str],
    exit_code: int = 0,
    status: CheckStatus = CheckStatus.OK,
    output: str = "HTTP OK",
    timed_out: bool = False,
    duration_seconds: float = 0.5,
) -> PluginResult:
    return PluginResult(
        command=command,
        exit_code=exit_code,
        status=status,
        output=output,
        timed_out=timed_out,
        duration_seconds=duration_seconds,
    )


# ---------------------------------------------------------------------------
# is_check_due — pure unit tests
# ---------------------------------------------------------------------------


class TestIsCheckDue:
    """Tests for the pure ``is_check_due`` function."""

    def test_never_run_is_due(self) -> None:
        """A check that has never been run should always be due."""
        assert is_check_due(interval_seconds=300, last_run_at=None) is True

    def test_due_when_interval_elapsed(self) -> None:
        """Check is due when elapsed time >= interval."""
        now = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
        last_run = now - timedelta(seconds=300)
        assert is_check_due(300, last_run, now=now) is True

    def test_not_due_when_interval_not_elapsed(self) -> None:
        """Check is not due when elapsed time < interval."""
        now = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
        last_run = now - timedelta(seconds=299)
        assert is_check_due(300, last_run, now=now) is False

    def test_exactly_at_interval_is_due(self) -> None:
        """Check is due when elapsed time exactly equals interval."""
        now = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
        last_run = now - timedelta(seconds=300)
        assert is_check_due(300, last_run, now=now) is True

    def test_zero_interval_is_always_due(self) -> None:
        """A check with interval_seconds=0 is always due."""
        now = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
        last_run = now - timedelta(seconds=1)
        assert is_check_due(0, last_run, now=now) is True

    def test_negative_interval_never_due(self) -> None:
        """A check with a negative interval should never be due."""
        now = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
        assert is_check_due(-1, None, now=now) is False

    def test_default_now_is_utc_aware(self) -> None:
        """When ``now`` is not provided, the function should use UTC."""
        result = is_check_due(interval_seconds=0, last_run_at=None)
        assert result is True


# ---------------------------------------------------------------------------
# get_due_check_ids — integration tests
# ---------------------------------------------------------------------------


class TestGetDueCheckIds:
    """Tests for ``get_due_check_ids`` with mocked store."""

    def test_all_checks_due_when_no_history(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
    ) -> None:
        """When no results exist, all registered checks should be due."""
        db_path = tmp_path / "check-results.sqlite3"
        monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(db_path))

        now = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
        due_ids = get_due_check_ids(now=now)

        assert sorted(due_ids) == ["disk-root", "http-example"]

    def test_no_checks_due_when_recently_run(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Checks recently run should not be due."""
        db_path = tmp_path / "check-results.sqlite3"
        monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(db_path))

        from app.store.check_results import persist_check_result
        import sqlite3

        now = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)

        # Seed results, then backdate created_at to 10s before now
        persist_check_result(
            "http-example",
            _fake_result(["/usr/lib/nagios/plugins/check_http", "-H", "example.com"]),
        )
        persist_check_result(
            "disk-root",
            _fake_result(["/usr/lib/nagios/plugins/check_disk", "-w", "20%", "-c", "10%", "-p", "/"]),
        )

        recent_ts = (now - timedelta(seconds=10)).isoformat()
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE check_results SET created_at = ?",
                (recent_ts,),
            )
            conn.commit()

        # http-example interval=300, disk-root interval=600
        # Both were run 10s ago, so neither is due
        due_ids = get_due_check_ids(now=now)
        assert due_ids == []

    def test_one_check_due_one_not(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Only checks past their interval should be due."""
        db_path = tmp_path / "check-results.sqlite3"
        monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(db_path))

        from app.store.check_results import persist_check_result

        now = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)

        # http-example interval=300 — run 600s ago → due
        persist_check_result(
            "http-example",
            _fake_result(["/usr/lib/nagios/plugins/check_http", "-H", "example.com"]),
        )
        # Manually update created_at to be 600s in the past
        import sqlite3

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE check_results SET created_at = ? WHERE check_id = ?",
                ((now - timedelta(seconds=600)).isoformat(), "http-example"),
            )
            conn.commit()

        # disk-root interval=600 — run 300s ago → not due
        persist_check_result(
            "disk-root",
            _fake_result(["/usr/lib/nagios/plugins/check_disk", "-w", "20%", "-c", "10%", "-p", "/"]),
        )
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE check_results SET created_at = ? WHERE check_id = ?",
                ((now - timedelta(seconds=300)).isoformat(), "disk-root"),
            )
            conn.commit()

        due_ids = get_due_check_ids(now=now)
        assert due_ids == ["http-example"]


# ---------------------------------------------------------------------------
# run_due_checks — one scheduler execution
# ---------------------------------------------------------------------------


class TestRunDueChecks:
    """Tests for ``run_due_checks`` with mocked plugin runner."""

    def test_run_due_checks_executes_and_persists(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
    ) -> None:
        """``run_due_checks`` should run due checks and persist results."""
        db_path = tmp_path / "check-results.sqlite3"
        monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(db_path))

        now = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)

        # Mock the plugin runner to return a predictable result
        def fake_run(command: list[str], timeout_seconds: int = 10) -> PluginResult:
            return _fake_result(command, output="SCHEDULER OK")

        monkeypatch.setattr("app.scheduler.service.run_nagios_plugin", fake_run)

        results = run_due_checks(now=now)

        # Both checks have no history, so both should run
        assert len(results) == 2
        check_ids = {check_id for check_id, _ in results}
        assert check_ids == {"http-example", "disk-root"}

        for check_id, result in results:
            assert result.output == "SCHEDULER OK"

        # Verify results were persisted
        import sqlite3

        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT check_id, output FROM check_results ORDER BY check_id"
            ).fetchall()

        assert len(rows) == 2
        assert rows[0] == ("disk-root", "SCHEDULER OK")
        assert rows[1] == ("http-example", "SCHEDULER OK")

    def test_run_due_checks_skips_non_due(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
    ) -> None:
        """``run_due_checks`` should skip checks that are not due."""
        db_path = tmp_path / "check-results.sqlite3"
        monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(db_path))

        from app.store.check_results import persist_check_result
        import sqlite3

        now = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)

        # Seed a recent result for both checks, then backdate to 10s before now
        persist_check_result(
            "http-example",
            _fake_result(["/usr/lib/nagios/plugins/check_http", "-H", "example.com"]),
        )
        persist_check_result(
            "disk-root",
            _fake_result(["/usr/lib/nagios/plugins/check_disk", "-w", "20%", "-c", "10%", "-p", "/"]),
        )

        recent_ts = (now - timedelta(seconds=10)).isoformat()
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE check_results SET created_at = ?",
                (recent_ts,),
            )
            conn.commit()

        def fake_run(command: list[str], timeout_seconds: int = 10) -> PluginResult:
            return _fake_result(command, output="SHOULD NOT RUN")

        monkeypatch.setattr("app.scheduler.service.run_nagios_plugin", fake_run)

        results = run_due_checks(now=now)

        # Both were run 10s ago, so neither is due
        assert results == []


# ---------------------------------------------------------------------------
# API-level test for POST /api/v1/scheduler/run
# ---------------------------------------------------------------------------


class TestSchedulerApi:
    """Tests for the scheduler API endpoint."""

    def test_scheduler_run_returns_executed_checks(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
    ) -> None:
        """POST /api/v1/scheduler/run should return executed check entries."""
        db_path = tmp_path / "check-results.sqlite3"
        monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(db_path))

        def fake_run(command: list[str], timeout_seconds: int = 10) -> PluginResult:
            return _fake_result(command, output="SCHEDULER OK")

        monkeypatch.setattr("app.scheduler.service.run_nagios_plugin", fake_run)

        client = TestClient(app)
        response = client.post("/api/v1/scheduler/run")

        assert response.status_code == 200
        body = response.json()
        assert "executed" in body
        executed = body["executed"]

        assert len(executed) == 2
        check_ids = {entry["check_id"] for entry in executed}
        assert check_ids == {"http-example", "disk-root"}

        for entry in executed:
            assert entry["status"] == "OK"
            assert entry["output"] == "SCHEDULER OK"
            assert entry["duration_seconds"] >= 0

    def test_scheduler_run_empty_when_none_due(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
    ) -> None:
        """POST /api/v1/scheduler/run should return empty list when none due."""
        db_path = tmp_path / "check-results.sqlite3"
        monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(db_path))

        from app.store.check_results import persist_check_result

        # Seed recent results so nothing is due
        persist_check_result(
            "http-example",
            _fake_result(["/usr/lib/nagios/plugins/check_http", "-H", "example.com"]),
        )
        persist_check_result(
            "disk-root",
            _fake_result(["/usr/lib/nagios/plugins/check_disk", "-w", "20%", "-c", "10%", "-p", "/"]),
        )

        def fake_run(command: list[str], timeout_seconds: int = 10) -> PluginResult:
            return _fake_result(command, output="SHOULD NOT RUN")

        monkeypatch.setattr("app.scheduler.service.run_nagios_plugin", fake_run)

        client = TestClient(app)
        response = client.post("/api/v1/scheduler/run")

        assert response.status_code == 200
        body = response.json()
        assert body == {"executed": []}
