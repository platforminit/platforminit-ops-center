from __future__ import annotations

from pathlib import PurePosixPath

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator

from app.runner.nagios import run_nagios_plugin
from app.runner.models import PluginResult

ALLOWED_PLUGIN_DIR = PurePosixPath("/usr/lib/nagios/plugins")
ALLOWED_PREFIX = f"{ALLOWED_PLUGIN_DIR}/"

# ---------------------------------------------------------------------------
# In-memory check registry
# ---------------------------------------------------------------------------

_CHECK_REGISTRY: dict[str, tuple[str, ...]] = {
    "http-example": (
        "/usr/lib/nagios/plugins/check_http",
        "-H",
        "example.com",
    ),
    "disk-root": (
        "/usr/lib/nagios/plugins/check_disk",
        "-w",
        "20%",
        "-c",
        "10%",
        "-p",
        "/",
    ),
}


def get_registered_checks() -> dict[str, list[str]]:
    """Return command copies so callers cannot mutate the registry."""
    return {
        check_id: list(command)
        for check_id, command in _CHECK_REGISTRY.items()
    }


def get_registered_command(check_id: str) -> list[str] | None:
    """Return the command list for *check_id*, or *None* if unknown."""
    command = _CHECK_REGISTRY.get(check_id)
    return list(command) if command is not None else None


def validate_command_list(command: list[str]) -> list[str]:
    if not command:
        raise ValueError("command must contain at least 1 element")

    if len(command) > 20:
        raise ValueError("command must contain at most 20 elements")

    for i, element in enumerate(command):
        if not element:
            raise ValueError(f"command[{i}] must be non-empty")
        if len(element) > 512:
            raise ValueError(f"command[{i}] exceeds maximum length of 512")

    executable = PurePosixPath(command[0])
    if (
        not executable.is_absolute()
        or executable.parent != ALLOWED_PLUGIN_DIR
        or ".." in executable.parts
    ):
        raise ValueError(f"command[0] must be an absolute path under {ALLOWED_PREFIX}")

    return command


# ---------------------------------------------------------------------------
# Existing /api/v1/checks/run  (unchanged)
# ---------------------------------------------------------------------------


class RunCheckRequest(BaseModel):
    command: list[str]
    timeout_seconds: int = Field(default=10, ge=1, le=30)

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: list[str]) -> list[str]:
        return validate_command_list(v)


class RunCheckResponse(BaseModel):
    result: PluginResult


def run_check(payload: RunCheckRequest) -> RunCheckResponse:
    result = run_nagios_plugin(
        command=payload.command,
        timeout_seconds=payload.timeout_seconds,
    )
    return RunCheckResponse(result=result)


# ---------------------------------------------------------------------------
# New: GET /api/v1/checks
# ---------------------------------------------------------------------------


class CheckEntry(BaseModel):
    check_id: str


class ListChecksResponse(BaseModel):
    checks: list[CheckEntry]


def list_checks() -> ListChecksResponse:
    return ListChecksResponse(
        checks=[
            CheckEntry(check_id=check_id)
            for check_id in sorted(get_registered_checks())
        ]
    )


# ---------------------------------------------------------------------------
# New: POST /api/v1/checks/{check_id}/run
# ---------------------------------------------------------------------------


class RunRegisteredCheckRequest(BaseModel):
    timeout_seconds: int = Field(default=10, ge=1, le=30)


class RunRegisteredCheckResponse(BaseModel):
    check_id: str
    result: PluginResult


def run_registered_check(check_id: str, payload: RunRegisteredCheckRequest) -> RunRegisteredCheckResponse:
    command = get_registered_command(check_id)
    if command is None:
        raise HTTPException(status_code=404, detail=f"Unknown check_id: {check_id}")

    validate_command_list(command)

    result = run_nagios_plugin(
        command=command,
        timeout_seconds=payload.timeout_seconds,
    )
    return RunRegisteredCheckResponse(check_id=check_id, result=result)
