"""Minimal MVP authentication guard for the Ops Center API.

Default mode is local-dev friendly (auth disabled).
When enabled, requires ``Authorization: Bearer <token>`` on sensitive endpoints.
"""

from __future__ import annotations

import secrets

from fastapi import HTTPException, Request, status

from app.core.config import load_settings


async def require_auth(request: Request) -> None:
    """FastAPI dependency that enforces bearer-token authentication.

    If ``OPS_CENTER_AUTH_ENABLED`` is ``false`` (the default), this
    dependency is a no-op.

    If enabled, the request **must** include an ``Authorization: Bearer
    <token>`` header whose value matches ``OPS_CENTER_API_TOKEN``.
    Missing or invalid tokens result in a 401 response.

    Token comparison uses ``secrets.compare_digest()`` to prevent
    timing side-channel attacks on the bearer token.
    """
    settings = load_settings()

    if not settings.auth_enabled:
        return

    token = settings.api_token
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

    if not secrets.compare_digest(provided_token, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
            headers={"WWW-Authenticate": "Bearer"},
        )
