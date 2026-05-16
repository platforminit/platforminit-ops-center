"""Inventory API — host and service metadata endpoints."""

from __future__ import annotations

from pydantic import BaseModel

from app.store.inventory import list_hosts, list_services


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class HostEntry(BaseModel):
    id: int
    name: str
    environment: str
    criticality: str
    owner: str
    runbook_url: str
    created_at: str
    updated_at: str


class ServiceEntry(BaseModel):
    id: int
    name: str
    host_id: int
    environment: str
    criticality: str
    owner: str
    runbook_url: str
    created_at: str
    updated_at: str


class ListHostsResponse(BaseModel):
    hosts: list[HostEntry]


class ListServicesResponse(BaseModel):
    services: list[ServiceEntry]


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def _host_entry_from_record(record) -> HostEntry:
    return HostEntry(
        id=record.id,
        name=record.name,
        environment=record.environment,
        criticality=record.criticality,
        owner=record.owner,
        runbook_url=record.runbook_url,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _service_entry_from_record(record) -> ServiceEntry:
    return ServiceEntry(
        id=record.id,
        name=record.name,
        host_id=record.host_id,
        environment=record.environment,
        criticality=record.criticality,
        owner=record.owner,
        runbook_url=record.runbook_url,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def list_hosts_handler() -> ListHostsResponse:
    """Return all hosts in the inventory."""
    records = list_hosts()
    return ListHostsResponse(
        hosts=[_host_entry_from_record(record) for record in records]
    )


def list_services_handler() -> ListServicesResponse:
    """Return all services in the inventory."""
    records = list_services()
    return ListServicesResponse(
        services=[_service_entry_from_record(record) for record in records]
    )
