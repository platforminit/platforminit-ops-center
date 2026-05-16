"""Inventory router — host and service metadata endpoints."""

from fastapi import APIRouter

from app.api.inventory import (
    ListHostsResponse,
    ListServicesResponse,
    list_hosts_handler,
    list_services_handler,
)

router = APIRouter(prefix="/api/v1", tags=["inventory"])


@router.get("/hosts", response_model=ListHostsResponse)
def hosts_list() -> ListHostsResponse:
    return list_hosts_handler()


@router.get("/services", response_model=ListServicesResponse)
def services_list() -> ListServicesResponse:
    return list_services_handler()
