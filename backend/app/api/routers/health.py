"""Health check router — unauthenticated read-only endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Return a simple health-check response."""
    return {"status": "ok"}
