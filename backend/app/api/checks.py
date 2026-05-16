from __future__ import annotations

from pathlib import PurePosixPath

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator

from app.runner.nagios import run_nagios_plugin
from app.runner.models import PluginResult
from app.store.check_results import (
    DEFAULT_HISTORY_LIMIT,
    CheckResultRecord,
    get_check_history,
    get_latest_results,
    get_problems,
    persist_check_result,
)

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
    persist_check_result(check_id, result)
    return RunRegisteredCheckResponse(check_id=check_id, result=result)


# ---------------------------------------------------------------------------
# New: persisted check result read APIs
# ---------------------------------------------------------------------------


class CheckResultEntry(BaseModel):
    id: int
    check_id: str
    status: str
    output: str
    perfdata: str | None
    stderr: str | None
    exit_code: int
    duration_seconds: float
    timed_out: bool
    created_at: str


class CheckHistoryResponse(BaseModel):
    check_id: str
    results: list[CheckResultEntry]


class LatestResultsResponse(BaseModel):
    results: list[CheckResultEntry]


def _entry_from_record(record: CheckResultRecord) -> CheckResultEntry:
    return CheckResultEntry(
        id=record.id,
        check_id=record.check_id,
        status=record.status,
        output=record.output,
        perfdata=record.perfdata,
        stderr=record.stderr,
        exit_code=record.exit_code,
        duration_seconds=record.duration_seconds,
        timed_out=record.timed_out,
        created_at=record.created_at,
    )


def check_history(
    check_id: str,
    limit: int = DEFAULT_HISTORY_LIMIT,
) -> CheckHistoryResponse:
    if get_registered_command(check_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown check_id: {check_id}")

    return CheckHistoryResponse(
        check_id=check_id,
        results=[_entry_from_record(record) for record in get_check_history(check_id, limit=limit)],
    )


def latest_results() -> LatestResultsResponse:
    check_ids = sorted(get_registered_checks())
    return LatestResultsResponse(
        results=[_entry_from_record(record) for record in get_latest_results(check_ids)]
    )


# ---------------------------------------------------------------------------
# New: GET /api/v1/problems
# ---------------------------------------------------------------------------


class ProblemEntry(BaseModel):
    check_id: str
    status: str
    output: str
    created_at: str
    duration_seconds: float
    timed_out: bool


class ProblemsResponse(BaseModel):
    problems: list[ProblemEntry]


def _problem_entry_from_record(record: CheckResultRecord) -> ProblemEntry:
    return ProblemEntry(
        check_id=record.check_id,
        status=record.status,
        output=record.output,
        created_at=record.created_at,
        duration_seconds=record.duration_seconds,
        timed_out=record.timed_out,
    )


def list_problems() -> ProblemsResponse:
    check_ids = sorted(get_registered_checks())
    return ProblemsResponse(
        problems=[
            _problem_entry_from_record(record)
            for record in get_problems(check_ids)
        ]
    )
