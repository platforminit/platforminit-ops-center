from __future__ import annotations

import sqlite3
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.checks import get_registered_checks
from app.main import app
from app.runner.models import CheckStatus, PluginResult


def _fake_result(
    command: list[str],
    exit_code: int = 0,
    status: CheckStatus = CheckStatus.OK,
    output: str = "HTTP OK",
    timed_out: bool = False,
    duration_seconds: float = 0.5,
    perfdata: str | None = None,
    stderr: str | None = None,
) -> PluginResult:
    return PluginResult(
        command=command,
        exit_code=exit_code,
        status=status,
        output=output,
        timed_out=timed_out,
        duration_seconds=duration_seconds,
        perfdata=perfdata,
        stderr=stderr,
    )


def _isolate_results_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(tmp_path / "check-results.sqlite3"))


# ---------------------------------------------------------------------------
# Existing POST /api/v1/checks/run tests (unchanged)
# ---------------------------------------------------------------------------


def test_checks_run_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], timeout_seconds: int = 10) -> PluginResult:
        return _fake_result(command)

    monkeypatch.setattr("app.api.checks.run_nagios_plugin", fake_run)

    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/run",
        json={
            "command": ["/usr/lib/nagios/plugins/check_http", "-H", "example.com"],
            "timeout_seconds": 10,
        },
    )

    assert response.status_code == 200
    body = response.json()
    result = body["result"]

    assert result["status"] == "OK"
    assert result["exit_code"] == 0
    assert "HTTP OK" in result["output"]
    assert result["timed_out"] is False
    assert result["duration_seconds"] >= 0
    assert result["command"] == ["/usr/lib/nagios/plugins/check_http", "-H", "example.com"]


def test_checks_run_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], timeout_seconds: int = 10) -> PluginResult:
        return _fake_result(
            command=command,
            exit_code=3,
            status=CheckStatus.UNKNOWN,
            output=f"Plugin timed out after {timeout_seconds}s",
            timed_out=True,
            duration_seconds=timeout_seconds,
        )

    monkeypatch.setattr("app.api.checks.run_nagios_plugin", fake_run)

    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/run",
        json={
            "command": ["/usr/lib/nagios/plugins/check_http", "-H", "example.com"],
            "timeout_seconds": 1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    result = body["result"]

    assert result["status"] == "UNKNOWN"
    assert result["exit_code"] == 3
    assert result["timed_out"] is True
    assert "timed out" in result["output"]


def test_checks_run_shell_string_rejected() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/run",
        json={
            "command": "check_http -H example.com",
            "timeout_seconds": 10,
        },
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("command" in str(e) for e in errors)


def test_checks_run_empty_command_rejected() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/run",
        json={
            "command": [],
            "timeout_seconds": 10,
        },
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("at least 1" in str(e).lower() for e in errors)


def test_checks_run_excessive_timeout_rejected() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/run",
        json={
            "command": ["/usr/lib/nagios/plugins/check_http", "-H", "example.com"],
            "timeout_seconds": 60,
        },
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("timeout" in str(e).lower() for e in errors)


def test_checks_run_disallowed_executable_rejected() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/run",
        json={
            "command": ["/usr/bin/python3", "-c", "print('hi')"],
            "timeout_seconds": 10,
        },
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("/usr/lib/nagios/plugins/" in str(e) for e in errors)


def test_checks_run_path_traversal_executable_rejected() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/run",
        json={
            "command": ["/usr/lib/nagios/plugins/../python3", "-c", "print('hi')"],
            "timeout_seconds": 10,
        },
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("/usr/lib/nagios/plugins/" in str(e) for e in errors)


def test_checks_run_empty_element_rejected() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/run",
        json={
            "command": ["/usr/lib/nagios/plugins/check_http", ""],
            "timeout_seconds": 10,
        },
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("non-empty" in str(e).lower() for e in errors)


def test_checks_run_element_too_long_rejected() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/run",
        json={
            "command": ["/usr/lib/nagios/plugins/check_http", "A" * 600],
            "timeout_seconds": 10,
        },
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("512" in str(e) for e in errors)


def test_checks_run_too_many_elements_rejected() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/run",
        json={
            "command": ["/usr/lib/nagios/plugins/check_http"] + ["-a"] * 20,
            "timeout_seconds": 10,
        },
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("20" in str(e) for e in errors)


# ---------------------------------------------------------------------------
# GET /api/v1/checks — metadata listing tests
# ---------------------------------------------------------------------------


def test_checks_list_returns_registered_checks() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/checks")

    assert response.status_code == 200
    body = response.json()
    assert "checks" in body
    checks = body["checks"]

    # Should contain the two initial registry entries
    check_ids = {c["check_id"] for c in checks}
    assert "http-example" in check_ids
    assert "disk-root" in check_ids


def test_checks_list_metadata_fields() -> None:
    """Each check entry exposes all required metadata fields."""
    client = TestClient(app)
    response = client.get("/api/v1/checks")
    assert response.status_code == 200
    checks = response.json()["checks"]

    http_entry = next(c for c in checks if c["check_id"] == "http-example")

    assert http_entry["name"] == "HTTP Example"
    assert http_entry["description"] == "Check that example.com returns HTTP 200 OK"
    assert http_entry["category"] == "web"
    assert http_entry["severity"] == "critical"
    assert http_entry["runbook_url"] == "https://example.com/runbooks/http-example"
    assert http_entry["interval_seconds"] == 300

    disk_entry = next(c for c in checks if c["check_id"] == "disk-root")

    assert disk_entry["name"] == "Disk Root"
    assert disk_entry["description"] == "Check available disk space on root filesystem"
    assert disk_entry["category"] == "system"
    assert disk_entry["severity"] == "warning"
    assert disk_entry["runbook_url"] == "https://example.com/runbooks/disk-root"
    assert disk_entry["interval_seconds"] == 600


def test_checks_list_does_not_expose_command() -> None:
    """Registered check listing must not expose raw command details."""
    client = TestClient(app)
    response = client.get("/api/v1/checks")
    assert response.status_code == 200
    checks = response.json()["checks"]

    for entry in checks:
        assert "command" not in entry, (
            f"check '{entry['check_id']}' must not expose 'command'"
        )

    assert "/usr/lib/nagios/plugins" not in response.text


def test_registered_check_metadata_is_immutable_and_commandless() -> None:
    registry = get_registered_checks()

    with pytest.raises(TypeError):
        registry["new-check"] = registry["http-example"]  # type: ignore[index]

    http_entry = registry["http-example"]
    assert not hasattr(http_entry, "command")

    with pytest.raises(FrozenInstanceError):
        http_entry.name = "Changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# New: POST /api/v1/checks/{check_id}/run tests
# ---------------------------------------------------------------------------


def test_checks_run_registered_ok(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_results_db(monkeypatch, tmp_path)

    def fake_run(command: list[str], timeout_seconds: int = 10) -> PluginResult:
        return _fake_result(command)

    monkeypatch.setattr("app.api.checks.run_nagios_plugin", fake_run)

    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/http-example/run",
        json={"timeout_seconds": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["check_id"] == "http-example"
    result = body["result"]

    assert result["status"] == "OK"
    assert result["exit_code"] == 0
    assert result["command"] == [
        "/usr/lib/nagios/plugins/check_http",
        "-H",
        "example.com",
    ]


def test_checks_run_registered_unknown_check_id() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/nonexistent-check/run",
        json={"timeout_seconds": 10},
    )

    assert response.status_code == 404
    body = response.json()
    assert "nonexistent-check" in body["detail"]


def test_checks_run_registered_disk_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_results_db(monkeypatch, tmp_path)

    def fake_run(command: list[str], timeout_seconds: int = 10) -> PluginResult:
        return _fake_result(command, output="DISK OK")

    monkeypatch.setattr("app.api.checks.run_nagios_plugin", fake_run)

    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/disk-root/run",
        json={"timeout_seconds": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["check_id"] == "disk-root"
    result = body["result"]

    assert result["status"] == "OK"
    assert result["command"] == [
        "/usr/lib/nagios/plugins/check_disk",
        "-w",
        "20%",
        "-c",
        "10%",
        "-p",
        "/",
    ]
    assert "DISK OK" in result["output"]


def test_checks_run_registered_persists_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    database_path = tmp_path / "check-results.sqlite3"
    monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(database_path))

    def fake_run(command: list[str], timeout_seconds: int = 10) -> PluginResult:
        return _fake_result(
            command,
            exit_code=2,
            status=CheckStatus.CRITICAL,
            output="HTTP CRITICAL",
            duration_seconds=1.25,
            perfdata="time=1.25s",
            stderr="connection refused",
        )

    monkeypatch.setattr("app.api.checks.run_nagios_plugin", fake_run)

    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/http-example/run",
        json={"timeout_seconds": 10},
    )

    assert response.status_code == 200

    with sqlite3.connect(database_path) as connection:
        row = connection.execute("SELECT * FROM check_results").fetchone()

    assert row is not None
    assert row[1] == "http-example"
    assert row[2] == "CRITICAL"
    assert row[3] == "HTTP CRITICAL"
    assert row[4] == "time=1.25s"
    assert row[5] == "connection refused"
    assert row[6] == 2
    assert row[7] == 1.25
    assert row[8] == 0
    assert row[9]


def test_checks_run_raw_ad_hoc_does_not_persist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    database_path = tmp_path / "check-results.sqlite3"
    monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(database_path))

    def fake_run(command: list[str], timeout_seconds: int = 10) -> PluginResult:
        return _fake_result(command)

    monkeypatch.setattr("app.api.checks.run_nagios_plugin", fake_run)

    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/run",
        json={
            "command": ["/usr/lib/nagios/plugins/check_http", "-H", "example.com"],
            "timeout_seconds": 10,
        },
    )

    assert response.status_code == 200
    assert not database_path.exists()


def test_checks_history_returns_persisted_results_newest_first(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    database_path = tmp_path / "check-results.sqlite3"
    monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(database_path))
    outputs = iter(["first", "second"])

    def fake_run(command: list[str], timeout_seconds: int = 10) -> PluginResult:
        return _fake_result(command, output=next(outputs))

    monkeypatch.setattr("app.api.checks.run_nagios_plugin", fake_run)

    client = TestClient(app)
    first_response = client.post("/api/v1/checks/http-example/run", json={"timeout_seconds": 10})
    second_response = client.post("/api/v1/checks/http-example/run", json={"timeout_seconds": 10})
    assert first_response.status_code == 200
    assert second_response.status_code == 200

    response = client.get("/api/v1/checks/http-example/history?limit=1")

    assert response.status_code == 200
    body = response.json()
    assert body["check_id"] == "http-example"
    assert len(body["results"]) == 1
    assert body["results"][0]["output"] == "second"
    assert body["results"][0]["check_id"] == "http-example"
    assert body["results"][0]["created_at"]


def test_checks_history_unknown_check_id() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/checks/nonexistent-check/history")

    assert response.status_code == 404


def test_latest_results_returns_latest_per_registered_check(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    database_path = tmp_path / "check-results.sqlite3"
    monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(database_path))
    outputs = iter(["http-old", "disk-current", "http-current"])

    def fake_run(command: list[str], timeout_seconds: int = 10) -> PluginResult:
        return _fake_result(command, output=next(outputs))

    monkeypatch.setattr("app.api.checks.run_nagios_plugin", fake_run)

    client = TestClient(app)
    http_old_response = client.post("/api/v1/checks/http-example/run", json={"timeout_seconds": 10})
    disk_response = client.post("/api/v1/checks/disk-root/run", json={"timeout_seconds": 10})
    http_current_response = client.post(
        "/api/v1/checks/http-example/run",
        json={"timeout_seconds": 10},
    )
    assert http_old_response.status_code == 200
    assert disk_response.status_code == 200
    assert http_current_response.status_code == 200

    response = client.get("/api/v1/results/latest")

    assert response.status_code == 200
    results = response.json()["results"]
    outputs_by_check_id = {result["check_id"]: result["output"] for result in results}

    assert outputs_by_check_id == {
        "disk-root": "disk-current",
        "http-example": "http-current",
    }


# ---------------------------------------------------------------------------
# New: GET /api/v1/problems tests
# ---------------------------------------------------------------------------


def test_problems_empty_when_no_results(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_results_db(monkeypatch, tmp_path)

    client = TestClient(app)
    response = client.get("/api/v1/problems")

    assert response.status_code == 200
    body = response.json()
    assert body == {"problems": []}


def test_problems_excludes_ok(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_results_db(monkeypatch, tmp_path)
    outputs = iter(["HTTP OK", "DISK CRITICAL"])

    def fake_run(command: list[str], timeout_seconds: int = 10) -> PluginResult:
        output = next(outputs)
        status = CheckStatus.CRITICAL if "CRITICAL" in output else CheckStatus.OK
        exit_code = 2 if "CRITICAL" in output else 0
        return _fake_result(command, exit_code=exit_code, status=status, output=output)

    monkeypatch.setattr("app.api.checks.run_nagios_plugin", fake_run)

    client = TestClient(app)
    client.post("/api/v1/checks/http-example/run", json={"timeout_seconds": 10})
    client.post("/api/v1/checks/disk-root/run", json={"timeout_seconds": 10})

    response = client.get("/api/v1/problems")
    assert response.status_code == 200
    problems = response.json()["problems"]

    assert len(problems) == 1
    assert problems[0]["check_id"] == "disk-root"
    assert problems[0]["status"] == "CRITICAL"
    assert problems[0]["output"] == "DISK CRITICAL"
    assert problems[0]["created_at"]
    assert problems[0]["duration_seconds"] == 0.5
    assert problems[0]["timed_out"] is False


def test_problems_returns_critical_warning_unknown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_results_db(monkeypatch, tmp_path)
    outputs = iter(["HTTP WARNING", "DISK CRITICAL", "HTTP UNKNOWN"])

    def fake_run(command: list[str], timeout_seconds: int = 10) -> PluginResult:
        output = next(outputs)
        if "WARNING" in output:
            status = CheckStatus.WARNING
            exit_code = 1
        elif "CRITICAL" in output:
            status = CheckStatus.CRITICAL
            exit_code = 2
        else:
            status = CheckStatus.UNKNOWN
            exit_code = 3
        return _fake_result(command, exit_code=exit_code, status=status, output=output)

    monkeypatch.setattr("app.api.checks.run_nagios_plugin", fake_run)

    client = TestClient(app)
    client.post("/api/v1/checks/http-example/run", json={"timeout_seconds": 10})
    client.post("/api/v1/checks/disk-root/run", json={"timeout_seconds": 10})
    client.post("/api/v1/checks/http-example/run", json={"timeout_seconds": 10})

    response = client.get("/api/v1/problems")
    assert response.status_code == 200
    problems = response.json()["problems"]

    assert len(problems) == 2
    statuses = {p["status"] for p in problems}
    assert statuses == {"CRITICAL", "UNKNOWN"}
    assert "WARNING" not in {p["status"] for p in problems}


def test_problems_sorted_by_severity_then_newest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_results_db(monkeypatch, tmp_path)
    outputs = iter(
        [
            "http WARNING",
            "disk CRITICAL",
            "other UNKNOWN",
        ]
    )

    def fake_run(command: list[str], timeout_seconds: int = 10) -> PluginResult:
        output = next(outputs)
        if "CRITICAL" in output:
            status = CheckStatus.CRITICAL
            exit_code = 2
        elif "WARNING" in output:
            status = CheckStatus.WARNING
            exit_code = 1
        else:
            status = CheckStatus.UNKNOWN
            exit_code = 3
        return _fake_result(command, exit_code=exit_code, status=status, output=output)

    monkeypatch.setattr("app.api.checks.run_nagios_plugin", fake_run)

    client = TestClient(app)
    client.post("/api/v1/checks/http-example/run", json={"timeout_seconds": 10})
    client.post("/api/v1/checks/disk-root/run", json={"timeout_seconds": 10})

    # Register a third check for UNKNOWN
    monkeypatch.setattr(
        "app.api.checks.get_registered_checks",
        lambda: {"http-example": [], "disk-root": [], "other-check": []},
    )

    # Manually insert an UNKNOWN result for the third check
    from app.store.check_results import persist_check_result

    persist_check_result(
        "other-check",
        _fake_result(
            ["/usr/lib/nagios/plugins/check_dummy"],
            exit_code=3,
            status=CheckStatus.UNKNOWN,
            output="other UNKNOWN",
        ),
    )

    response = client.get("/api/v1/problems")
    assert response.status_code == 200
    problems = response.json()["problems"]

    assert len(problems) == 3
    # Order should be: CRITICAL first, then WARNING, then UNKNOWN
    assert problems[0]["status"] == "CRITICAL"
    assert problems[1]["status"] == "WARNING"
    assert problems[2]["status"] == "UNKNOWN"


def test_problems_response_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_results_db(monkeypatch, tmp_path)

    def fake_run(command: list[str], timeout_seconds: int = 10) -> PluginResult:
        return _fake_result(
            command,
            exit_code=2,
            status=CheckStatus.CRITICAL,
            output="HTTP CRITICAL: connection refused",
            duration_seconds=2.5,
            timed_out=False,
        )

    monkeypatch.setattr("app.api.checks.run_nagios_plugin", fake_run)

    client = TestClient(app)
    client.post("/api/v1/checks/http-example/run", json={"timeout_seconds": 10})

    response = client.get("/api/v1/problems")
    assert response.status_code == 200
    problem = response.json()["problems"][0]

    assert set(problem.keys()) == {
        "check_id",
        "status",
        "output",
        "created_at",
        "duration_seconds",
        "timed_out",
    }
    assert problem["check_id"] == "http-example"
    assert problem["status"] == "CRITICAL"
    assert problem["output"] == "HTTP CRITICAL: connection refused"
    assert problem["duration_seconds"] == 2.5
    assert problem["timed_out"] is False
