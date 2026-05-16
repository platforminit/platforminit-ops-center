"""Centralized configuration for the PlatformInit Ops Center.

All environment-variable access is consolidated here so that consumers
import a single ``Settings`` dataclass rather than calling ``os.environ``
directly.  This makes defaults, overrides, and future config sources
(e.g. a config file or Vault) easier to manage.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Immutable settings loaded from environment variables.

    Every field has a local-dev-friendly default so the application can
    run without any environment configuration.
    """

    #: Master switch for bearer-token authentication on mutation endpoints.
    auth_enabled: bool = False

    #: Expected bearer token when ``auth_enabled`` is ``True``.
    api_token: str | None = None

    #: Allow ad-hoc (arbitrary command) check execution.
    enable_adhoc_checks: bool = False

    #: Filesystem path for the SQLite database that stores check results,
    #: inventory, acknowledgements, comments, and downtimes.
    check_results_db: Path | None = None


def _parse_bool(raw: str | None, default: str = "false") -> bool:
    """Parse an environment-variable string into a boolean.

    Truthy values: ``"1"``, ``"true"``, ``"yes"`` (case-insensitive).
    Everything else (including unset) is ``False``.
    """
    value = (raw or default).strip().lower()
    return value in ("1", "true", "yes")


def load_settings() -> Settings:
    """Read settings from the process environment.

    This is the only function in the codebase that calls
    ``os.environ.get`` for the four MVP configuration variables.
    """
    return Settings(
        auth_enabled=_parse_bool(os.environ.get("OPS_CENTER_AUTH_ENABLED")),
        api_token=os.environ.get("OPS_CENTER_API_TOKEN") or None,
        enable_adhoc_checks=_parse_bool(
            os.environ.get("OPS_CENTER_ENABLE_ADHOC_CHECKS")
        ),
        check_results_db=(
            Path(p) if (p := os.environ.get("PLATFORMINIT_CHECK_RESULTS_DB")) else None
        ),
    )
