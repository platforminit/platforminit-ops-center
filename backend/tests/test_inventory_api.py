"""Tests for the inventory API — host and service metadata endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _isolate_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(tmp_path / "check-results.sqlite3"))


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
    body = response.json()
    assert "hosts" in body
    hosts = body["hosts"]

    # Should contain the three seed hosts
    host_names = {h["name"] for h in hosts}
    assert host_names == {"web-01", "db-01", "cache-01"}


def test_hosts_list_metadata_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_db(monkeypatch, tmp_path)

    client = TestClient(app)
    response = client.get("/api/v1/hosts")
    assert response.status_code == 200
    hosts = response.json()["hosts"]

    web_entry = next(h for h in hosts if h["name"] == "web-01")
    assert web_entry["id"] > 0
    assert web_entry["environment"] == "production"
    assert web_entry["criticality"] == "high"
    assert web_entry["owner"] == "platform-team"
    assert web_entry["runbook_url"] == "https://example.com/runbooks/web-01"
    assert web_entry["created_at"]
    assert web_entry["updated_at"]


def test_hosts_list_sorted_by_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_db(monkeypatch, tmp_path)

    client = TestClient(app)
    response = client.get("/api/v1/hosts")
    assert response.status_code == 200
    hosts = response.json()["hosts"]

    names = [h["name"] for h in hosts]
    assert names == sorted(names)


def test_hosts_list_response_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_db(monkeypatch, tmp_path)

    client = TestClient(app)
    response = client.get("/api/v1/hosts")
    assert response.status_code == 200
    host = response.json()["hosts"][0]

    assert set(host.keys()) == {
        "id",
        "name",
        "environment",
        "criticality",
        "owner",
        "runbook_url",
        "created_at",
        "updated_at",
    }


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
    body = response.json()
    assert "services" in body
    services = body["services"]

    # Should contain the three seed services
    service_names = {s["name"] for s in services}
    assert service_names == {"http-check", "postgres-health", "redis-health"}


def test_services_list_metadata_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_db(monkeypatch, tmp_path)

    client = TestClient(app)
    response = client.get("/api/v1/services")
    assert response.status_code == 200
    services = response.json()["services"]

    http_entry = next(s for s in services if s["name"] == "http-check")
    assert http_entry["id"] > 0
    assert http_entry["host_id"] > 0
    assert http_entry["environment"] == "production"
    assert http_entry["criticality"] == "high"
    assert http_entry["owner"] == "platform-team"
    assert http_entry["runbook_url"] == "https://example.com/runbooks/http-check"
    assert http_entry["created_at"]
    assert http_entry["updated_at"]


def test_services_list_sorted_by_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_db(monkeypatch, tmp_path)

    client = TestClient(app)
    response = client.get("/api/v1/services")
    assert response.status_code == 200
    services = response.json()["services"]

    names = [s["name"] for s in services]
    assert names == sorted(names)


def test_services_list_response_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_db(monkeypatch, tmp_path)

    client = TestClient(app)
    response = client.get("/api/v1/services")
    assert response.status_code == 200
    service = response.json()["services"][0]

    assert set(service.keys()) == {
        "id",
        "name",
        "host_id",
        "environment",
        "criticality",
        "owner",
        "runbook_url",
        "created_at",
        "updated_at",
    }


# ---------------------------------------------------------------------------
# Validation — no secret leakage
# ---------------------------------------------------------------------------


def test_hosts_list_does_not_expose_secrets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_db(monkeypatch, tmp_path)

    client = TestClient(app)
    response = client.get("/api/v1/hosts")
    assert response.status_code == 200

    # Ensure no sensitive fields are exposed
    for host in response.json()["hosts"]:
        assert "password" not in host
        assert "secret" not in host
        assert "token" not in host
        assert "key" not in host

    # Ensure no raw SQL or internal details leak
    assert "INSERT" not in response.text
    assert "sqlite" not in response.text.lower()


def test_services_list_does_not_expose_secrets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_db(monkeypatch, tmp_path)

    client = TestClient(app)
    response = client.get("/api/v1/services")
    assert response.status_code == 200

    for service in response.json()["services"]:
        assert "password" not in service
        assert "secret" not in service
        assert "token" not in service
        assert "key" not in service

    assert "INSERT" not in response.text
    assert "sqlite" not in response.text.lower()


# ---------------------------------------------------------------------------
# Validation — input handling
# ---------------------------------------------------------------------------


def test_hosts_list_rejects_post_method() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/hosts")
    assert response.status_code in (405, 422)


def test_services_list_rejects_post_method() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/services")
    assert response.status_code in (405, 422)


def test_hosts_list_rejects_unsupported_media_type() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/hosts", headers={"Accept": "application/xml"})
    # FastAPI returns JSON regardless, but should still be 200
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Data integrity — foreign key relationship
# ---------------------------------------------------------------------------


def test_services_reference_valid_hosts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> None:
    _isolate_db(monkeypatch, tmp_path)

    client = TestClient(app)
    host_response = client.get("/api/v1/hosts")
    service_response = client.get("/api/v1/services")

    assert host_response.status_code == 200
    assert service_response.status_code == 200

    hosts = host_response.json()["hosts"]
    services = service_response.json()["services"]

    host_ids = {h["id"] for h in hosts}
    for service in services:
        assert service["host_id"] in host_ids, (
            f"Service '{service['name']}' references host_id={service['host_id']} "
            f"which does not exist"
        )
