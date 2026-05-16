"""Minimal MVP authentication guard for the Ops Center API.

Default mode is local-dev friendly (auth disabled).
When enabled, requires ``Authorization: Bearer <token>`` on sensitive endpoints.
"""

from __future__ import annotations

import os

from fastapi import HTTPException, Request, status


def _is_auth_enabled() -> bool:
    """Return ``True`` if API authentication is enabled.

    Controlled by the ``OPS_CENTER_AUTH_ENABLED`` environment variable.
    Defaults to ``"false"`` for local development.
    """
    raw = os.environ.get("OPS_CENTER_AUTH_ENABLED", "false").strip().lower()
    return raw in ("1", "true", "yes")


def _expected_token() -> str | None:
    """Return the expected API token, or ``None`` if not configured."""
    return os.environ.get("OPS_CENTER_API_TOKEN") or None


async def require_auth(request: Request) -> None:
    """FastAPI dependency that enforces bearer-token authentication.

    If ``OPS_CENTER_AUTH_ENABLED`` is ``false`` (the default), this
    dependency is a no-op.

    If enabled, the request **must** include an ``Authorization: Bearer
    <token>`` header whose value matches ``OPS_CENTER_API_TOKEN``.
    Missing or invalid tokens result in a 401 response.
    """
    if not _is_auth_enabled():
        return

    token = _expected_token()
    if token is None:
        # Auth is enabled but no token is configured — fail closed.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is enabled but OPS_CENTER_API_TOKEN is not configured",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    provided_token = auth_header[len("Bearer "):].strip()
    if not provided_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is empty",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if provided_token != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
            headers={"WWW-Authenticate": "Bearer"},
        )
