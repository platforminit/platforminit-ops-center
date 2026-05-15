from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.runner.models import CheckStatus, PluginResult


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
# New: GET /api/v1/checks tests
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

    # Registered check listing should not expose raw executable arguments.
    http_entry = next(c for c in checks if c["check_id"] == "http-example")
    assert "command" not in http_entry

    disk_entry = next(c for c in checks if c["check_id"] == "disk-root")
    assert "command" not in disk_entry


# ---------------------------------------------------------------------------
# New: POST /api/v1/checks/{check_id}/run tests
# ---------------------------------------------------------------------------


def test_checks_run_registered_ok(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_checks_run_registered_disk_root(monkeypatch: pytest.MonkeyPatch) -> None:
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
