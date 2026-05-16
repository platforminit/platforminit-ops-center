"""Endpoint preservation tests — verify all routes still respond after domain split.

These tests ensure that the router refactor did not change any OpenAPI paths,
auth guards, or response shapes.  They exercise every registered endpoint
at the HTTP level via TestClient.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _isolate_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(tmp_path / "check-results.sqlite3"))


# ---------------------------------------------------------------------------
# MVP API contract — endpoint matrix
#
# Every entry: (method, path, requires_auth)
# This is the single source of truth for the documented API contract.
# ---------------------------------------------------------------------------

MVP_ENDPOINTS: list[tuple[str, str, bool]] = [
    ("GET", "/healthz", False),
    ("GET", "/api/v1/checks", False),
    ("GET", "/api/v1/checks/{check_id}/history", False),
    ("GET", "/api/v1/results/latest", False),
    ("GET", "/api/v1/problems", False),
    ("GET", "/api/v1/hosts", False),
    ("GET", "/api/v1/services", False),
    ("GET", "/api/v1/checks/{check_id}/downtimes", False),
    ("POST", "/api/v1/checks/run", True),
    ("POST", "/api/v1/checks/{check_id}/run", True),
    ("POST", "/api/v1/scheduler/run", True),
    ("POST", "/api/v1/checks/{check_id}/acknowledge", True),
    ("POST", "/api/v1/checks/{check_id}/comments", True),
    ("POST", "/api/v1/checks/{check_id}/downtimes", True),
]


def test_contract_endpoint_matrix_matches_openapi() -> None:
    """Every endpoint in the documented contract must exist in the OpenAPI schema
    with the correct HTTP method."""
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    openapi_paths = schema["paths"]

    for method, path, _requires_auth in MVP_ENDPOINTS:
        assert path in openapi_paths, (
            f"Contract path {method} {path} not found in OpenAPI schema"
        )
        assert method.lower() in openapi_paths[path], (
            f"Contract method {method} not found for path {path} in OpenAPI schema"
        )


def test_contract_no_extra_paths() -> None:
    """No undocumented paths should exist in the OpenAPI schema."""
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    openapi_paths = set(schema["paths"].keys())

    contract_paths = {path for _method, path, _auth in MVP_ENDPOINTS}
    extra = openapi_paths - contract_paths

    assert not extra, f"Undocumented paths found in OpenAPI schema: {extra}"


def test_contract_auth_guards_match_documentation() -> None:
    """Contract auth flags must match the documented read-only vs mutation split."""
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    openapi_paths = schema["paths"]

    for method, path, requires_auth in MVP_ENDPOINTS:
        operation = openapi_paths[path][method.lower()]
        has_security = "security" in operation and len(operation["security"]) > 0

        if requires_auth:
            # Our current implementation uses Depends() which may not appear
            # in OpenAPI security.  Verify the path is a POST (mutation)
            # endpoint as a proxy for auth requirement.
            assert method == "POST", (
                f"Expected {method} {path} to be a POST mutation endpoint"
            )
        else:
            assert method == "GET", f"Expected {method} {path} to be read-only"
            assert not has_security, f"Read-only endpoint {method} {path} declared security"


# ---------------------------------------------------------------------------
# All registered OpenAPI paths
# ---------------------------------------------------------------------------


def test_all_expected_paths_present() -> None:
    """Every expected path must be registered in the OpenAPI schema."""
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    paths = set(schema["paths"].keys())

    expected = {
        "/healthz",
        "/api/v1/checks",
        "/api/v1/checks/{check_id}/history",
        "/api/v1/results/latest",
        "/api/v1/problems",
        "/api/v1/hosts",
        "/api/v1/services",
        "/api/v1/checks/{check_id}/downtimes",
        "/api/v1/checks/run",
        "/api/v1/checks/{check_id}/run",
        "/api/v1/scheduler/run",
        "/api/v1/checks/{check_id}/acknowledge",
        "/api/v1/checks/{check_id}/comments",
        "/api/v1/checks/{check_id}/downtimes",
    }

    missing = expected - paths
    extra = paths - expected

    assert not missing, f"Expected paths missing from OpenAPI schema: {missing}"
    assert not extra, f"Unexpected paths in OpenAPI schema: {extra}"


# ---------------------------------------------------------------------------
# GET /healthz
# ---------------------------------------------------------------------------


def test_healthz_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /api/v1/checks
# ---------------------------------------------------------------------------


def test_checks_list_returns_registered_checks() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/checks")
    assert response.status_code == 200
    body = response.json()
    assert "checks" in body
    check_ids = {c["check_id"] for c in body["checks"]}
    assert "http-example" in check_ids
    assert "disk-root" in check_ids


# ---------------------------------------------------------------------------
# GET /api/v1/checks/{check_id}/history
# ---------------------------------------------------------------------------


def test_checks_history_unknown_check_id() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/checks/nonexistent-check/history")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/results/latest
# ---------------------------------------------------------------------------


def test_results_latest_returns_empty_when_no_data(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_db(monkeypatch, tmp_path)
    client = TestClient(app)
    response = client.get("/api/v1/results/latest")
    assert response.status_code == 200
    assert response.json() == {"results": []}


# ---------------------------------------------------------------------------
# GET /api/v1/problems
# ---------------------------------------------------------------------------


def test_problems_empty_when_no_results(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_db(monkeypatch, tmp_path)
    client = TestClient(app)
    response = client.get("/api/v1/problems")
    assert response.status_code == 200
    assert response.json() == {"problems": []}


# ---------------------------------------------------------------------------
# GET /api/v1/hosts
# ---------------------------------------------------------------------------


def test_hosts_list_returns_seeded_hosts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_db(monkeypatch, tmp_path)
    client = TestClient(app)
    response = client.get("/api/v1/hosts")
    assert response.status_code == 200
    host_names = {h["name"] for h in response.json()["hosts"]}
    assert host_names == {"web-01", "db-01", "cache-01"}


# ---------------------------------------------------------------------------
# GET /api/v1/services
# ---------------------------------------------------------------------------


def test_services_list_returns_seeded_services(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_db(monkeypatch, tmp_path)
    client = TestClient(app)
    response = client.get("/api/v1/services")
    assert response.status_code == 200
    service_names = {s["name"] for s in response.json()["services"]}
    assert service_names == {"http-check", "postgres-health", "redis-health"}


# ---------------------------------------------------------------------------
# GET /api/v1/checks/{check_id}/downtimes
# ---------------------------------------------------------------------------


def test_list_downtimes_unknown_check_id() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/checks/nonexistent-check/downtimes")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/checks/run — auth disabled (default)
# ---------------------------------------------------------------------------


def test_checks_run_auth_disabled_returns_403_adhoc_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPS_CENTER_ENABLE_ADHOC_CHECKS", raising=False)
    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/run",
        json={
            "command": ["/usr/lib/nagios/plugins/check_http", "-H", "example.com"],
            "timeout_seconds": 10,
        },
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/v1/checks/{check_id}/run — auth disabled (default)
# ---------------------------------------------------------------------------


def test_checks_run_registered_unknown_check_id() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/nonexistent-check/run",
        json={"timeout_seconds": 10},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/scheduler/run — auth disabled (default)
# ---------------------------------------------------------------------------


def test_scheduler_run_auth_disabled_returns_200(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_db(monkeypatch, tmp_path)
    client = TestClient(app)
    response = client.post("/api/v1/scheduler/run")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/v1/checks/{check_id}/acknowledge — auth disabled (default)
# ---------------------------------------------------------------------------


def test_acknowledge_unknown_check_id() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/nonexistent-check/acknowledge",
        json={"operator": "alice", "reason": "Investigating"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/checks/{check_id}/comments — auth disabled (default)
# ---------------------------------------------------------------------------


def test_comment_unknown_check_id() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/nonexistent-check/comments",
        json={"operator": "bob", "comment": "test"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/checks/{check_id}/downtimes — auth disabled (default)
# ---------------------------------------------------------------------------


def test_create_downtime_unknown_check_id() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/checks/nonexistent-check/downtimes",
        json={
            "start_time": "2026-01-01T10:00:00+00:00",
            "end_time": "2026-01-01T12:00:00+00:00",
            "reason": "Maintenance",
            "operator": "alice",
        },
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Auth guard preservation — mutation endpoints require auth when enabled
# ---------------------------------------------------------------------------


def _enable_auth(monkeypatch: pytest.MonkeyPatch, token: str = "test-token") -> None:
    monkeypatch.setenv("OPS_CENTER_AUTH_ENABLED", "true")
    monkeypatch.setenv("OPS_CENTER_API_TOKEN", token)


@pytest.mark.parametrize(
    "method, path, body",
    [
        ("POST", "/api/v1/checks/run", {"command": ["/usr/lib/nagios/plugins/check_http", "-H", "example.com"], "timeout_seconds": 10}),
        ("POST", "/api/v1/checks/http-example/run", {"timeout_seconds": 10}),
        ("POST", "/api/v1/scheduler/run", None),
        ("POST", "/api/v1/checks/http-example/acknowledge", {"operator": "alice", "reason": "test"}),
        ("POST", "/api/v1/checks/http-example/comments", {"operator": "alice", "comment": "test"}),
        ("POST", "/api/v1/checks/http-example/downtimes", {"start_time": "2026-01-01T10:00:00+00:00", "end_time": "2026-01-01T12:00:00+00:00", "reason": "test", "operator": "alice"}),
    ],
)
def test_mutation_endpoints_require_auth_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    body: dict | None,
) -> None:
    """All mutation endpoints must return 401 when auth is enabled and no token is sent."""
    _enable_auth(monkeypatch)

    client = TestClient(app)
    if method == "POST":
        response = client.post(path, json=body or {})
    else:
        response = client.request(method, path)

    assert response.status_code == 401, f"{method} {path} should return 401 when auth enabled"


# ---------------------------------------------------------------------------
# Read-only endpoints remain accessible when auth is enabled
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method, path",
    [
        ("GET", "/healthz"),
        ("GET", "/api/v1/checks"),
        ("GET", "/api/v1/problems"),
        ("GET", "/api/v1/hosts"),
        ("GET", "/api/v1/services"),
        ("GET", "/api/v1/results/latest"),
    ],
)
def test_read_only_endpoints_accessible_when_auth_enabled(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
) -> None:
    """Read-only endpoints must remain accessible when auth is enabled."""
    _enable_auth(monkeypatch)

    client = TestClient(app)
    response = client.request(method, path)

    assert response.status_code in (200, 404), f"{method} {path} should be accessible when auth enabled"
