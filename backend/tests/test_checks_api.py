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
