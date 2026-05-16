from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Mapping

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from app.runner.nagios import run_nagios_plugin
from app.runner.models import PluginResult
from app.scheduler.service import run_due_checks
from app.store.check_results import (
    DEFAULT_HISTORY_LIMIT,
    AcknowledgementRecord,
    CheckResultRecord,
    get_acknowledgements,
    get_check_history,
    get_latest_results,
    get_problems,
    persist_acknowledgement,
    persist_check_result,
    persist_comment,
)
from app.store.downtimes import (
    DowntimeRecord,
    get_downtime_map,
    get_downtimes,
    persist_downtime,
)

ALLOWED_PLUGIN_DIR = PurePosixPath("/usr/lib/nagios/plugins")
ALLOWED_PREFIX = f"{ALLOWED_PLUGIN_DIR}/"
MAX_DOWNTIME_DURATION = timedelta(days=90)


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
# In-memory check registry — metadata-rich definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckDefinition:
    """Immutable metadata definition for a registered check."""

    check_id: str
    name: str
    description: str
    category: str
    severity: str
    runbook_url: str
    interval_seconds: int


@dataclass(frozen=True)
class _RegisteredCheckDefinition:
    """Internal immutable definition containing metadata and command details."""

    metadata: CheckDefinition
    command: tuple[str, ...]


_CHECK_DEFINITIONS: tuple[_RegisteredCheckDefinition, ...] = (
    _RegisteredCheckDefinition(
        metadata=CheckDefinition(
            check_id="http-example",
            name="HTTP Example",
            description="Check that example.com returns HTTP 200 OK",
            category="web",
            severity="critical",
            runbook_url="https://example.com/runbooks/http-example",
            interval_seconds=300,
        ),
        command=(
            "/usr/lib/nagios/plugins/check_http",
            "-H",
            "example.com",
        ),
    ),
    _RegisteredCheckDefinition(
        metadata=CheckDefinition(
            check_id="disk-root",
            name="Disk Root",
            description="Check available disk space on root filesystem",
            category="system",
            severity="warning",
            runbook_url="https://example.com/runbooks/disk-root",
            interval_seconds=600,
        ),
        command=(
            "/usr/lib/nagios/plugins/check_disk",
            "-w",
            "20%",
            "-c",
            "10%",
            "-p",
            "/",
        ),
    ),
)


for definition in _CHECK_DEFINITIONS:
    validate_command_list(list(definition.command))


_CHECK_REGISTRY: Mapping[str, CheckDefinition] = MappingProxyType(
    {definition.metadata.check_id: definition.metadata for definition in _CHECK_DEFINITIONS}
)
_CHECK_COMMANDS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {definition.metadata.check_id: definition.command for definition in _CHECK_DEFINITIONS}
)


def get_registered_checks() -> Mapping[str, CheckDefinition]:
    """Return immutable registry metadata without command details."""
    return _CHECK_REGISTRY


def get_registered_command(check_id: str) -> list[str] | None:
    """Return the command list for *check_id*, or *None* if unknown."""
    command = _CHECK_COMMANDS.get(check_id)
    return list(command) if command is not None else None


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


class CheckMetadata(BaseModel):
    check_id: str
    name: str
    description: str
    category: str
    severity: str
    runbook_url: str
    interval_seconds: int


class ListChecksResponse(BaseModel):
    checks: list[CheckMetadata]


def list_checks() -> ListChecksResponse:
    return ListChecksResponse(
        checks=[
            CheckMetadata(
                check_id=defn.check_id,
                name=defn.name,
                description=defn.description,
                category=defn.category,
                severity=defn.severity,
                runbook_url=defn.runbook_url,
                interval_seconds=defn.interval_seconds,
            )
            for defn in sorted(
                get_registered_checks().values(),
                key=lambda d: d.check_id,
            )
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
    acknowledged: bool
    acknowledged_by: str | None = None
    acknowledged_at: str | None = None
    acknowledged_reason: str | None = None
    in_downtime: bool = False


class ProblemsResponse(BaseModel):
    problems: list[ProblemEntry]


def _problem_entry_from_record(
    record: CheckResultRecord,
    ack: AcknowledgementRecord | None = None,
    in_downtime: bool = False,
) -> ProblemEntry:
    return ProblemEntry(
        check_id=record.check_id,
        status=record.status,
        output=record.output,
        created_at=record.created_at,
        duration_seconds=record.duration_seconds,
        timed_out=record.timed_out,
        acknowledged=ack is not None,
        acknowledged_by=ack.operator if ack else None,
        acknowledged_at=ack.created_at if ack else None,
        acknowledged_reason=ack.reason if ack else None,
        in_downtime=in_downtime,
    )


def list_problems() -> ProblemsResponse:
    check_ids = sorted(get_registered_checks())
    problems = get_problems(check_ids)
    ack_map = get_acknowledgements(check_ids)
    downtime_map = get_downtime_map(check_ids)
    return ProblemsResponse(
        problems=[
            _problem_entry_from_record(
                record,
                ack=ack_map.get(record.check_id),
                in_downtime=downtime_map.get(record.check_id, False),
            )
            for record in problems
        ]
    )


# ---------------------------------------------------------------------------
# New: POST /api/v1/checks/{check_id}/acknowledge
# ---------------------------------------------------------------------------


class AcknowledgeRequest(BaseModel):
    operator: str = Field(..., min_length=1, max_length=128)
    reason: str = Field(..., min_length=1, max_length=2000)

    @field_validator("operator", "reason")
    @classmethod
    def validate_non_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must contain non-whitespace text")
        return normalized


class AcknowledgeResponse(BaseModel):
    id: int
    check_id: str
    operator: str
    reason: str
    created_at: str


def acknowledge_check(check_id: str, payload: AcknowledgeRequest) -> AcknowledgeResponse:
    if get_registered_command(check_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown check_id: {check_id}")

    current_problems = get_problems([check_id])
    if not current_problems:
        raise HTTPException(
            status_code=409,
            detail="Cannot acknowledge a check without a current problem",
        )

    record = persist_acknowledgement(
        check_id=check_id,
        operator=payload.operator,
        reason=payload.reason,
    )
    return AcknowledgeResponse(
        id=record.id,
        check_id=record.check_id,
        operator=record.operator,
        reason=record.reason,
        created_at=record.created_at,
    )


# ---------------------------------------------------------------------------
# New: POST /api/v1/checks/{check_id}/comments
# ---------------------------------------------------------------------------


class CommentRequest(BaseModel):
    operator: str = Field(..., min_length=1, max_length=128)
    comment: str = Field(..., min_length=1, max_length=2000)

    @field_validator("operator", "comment")
    @classmethod
    def validate_non_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must contain non-whitespace text")
        return normalized


class CommentResponse(BaseModel):
    id: int
    check_id: str
    operator: str
    comment: str
    created_at: str


def add_comment(check_id: str, payload: CommentRequest) -> CommentResponse:
    if get_registered_command(check_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown check_id: {check_id}")

    record = persist_comment(
        check_id=check_id,
        operator=payload.operator,
        comment=payload.comment,
    )
    return CommentResponse(
        id=record.id,
        check_id=record.check_id,
        operator=record.operator,
        comment=record.comment,
        created_at=record.created_at,
    )


# ---------------------------------------------------------------------------
# New: POST /api/v1/scheduler/run
# ---------------------------------------------------------------------------


class SchedulerRunResponse(BaseModel):
    executed: list[SchedulerRunEntry]


class SchedulerRunEntry(BaseModel):
    check_id: str
    status: str
    output: str
    duration_seconds: float


def run_scheduler() -> SchedulerRunResponse:
    """Run all due registered checks and return the results."""
    results = run_due_checks()
    return SchedulerRunResponse(
        executed=[
            SchedulerRunEntry(
                check_id=check_id,
                status=result.status.value,
                output=result.output,
                duration_seconds=result.duration_seconds,
            )
            for check_id, result in results
        ]
    )


# ---------------------------------------------------------------------------
# New: POST /api/v1/checks/{check_id}/downtimes
#       GET /api/v1/checks/{check_id}/downtimes
# ---------------------------------------------------------------------------


class CreateDowntimeRequest(BaseModel):
    start_time: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="ISO-8601 timestamp with timezone",
    )
    end_time: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="ISO-8601 timestamp with timezone",
    )
    reason: str = Field(..., min_length=1, max_length=2000)
    operator: str = Field(..., min_length=1, max_length=128)

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_iso_timestamp(cls, value: str) -> str:
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None or dt.utcoffset() is None:
                raise ValueError("timestamp must be timezone-aware")
        except ValueError as exc:
            raise ValueError(
                f"value must be a valid timezone-aware ISO-8601 timestamp: {exc}"
            ) from exc
        return dt.astimezone(timezone.utc).isoformat()

    @field_validator("reason", "operator")
    @classmethod
    def validate_non_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must contain non-whitespace text")
        return normalized

    @model_validator(mode="after")
    def validate_window_bounds(self) -> "CreateDowntimeRequest":
        start = datetime.fromisoformat(self.start_time)
        end = datetime.fromisoformat(self.end_time)
        if end <= start:
            raise ValueError("end_time must be after start_time")
        if end - start > MAX_DOWNTIME_DURATION:
            raise ValueError("downtime window must not exceed 90 days")
        return self


class DowntimeEntry(BaseModel):
    id: int
    check_id: str
    start_time: str
    end_time: str
    reason: str
    operator: str
    created_at: str


class CreateDowntimeResponse(BaseModel):
    downtime: DowntimeEntry


class ListDowntimesResponse(BaseModel):
    downtimes: list[DowntimeEntry]


def _downtime_entry_from_record(record: DowntimeRecord) -> DowntimeEntry:
    return DowntimeEntry(
        id=record.id,
        check_id=record.check_id,
        start_time=record.start_time,
        end_time=record.end_time,
        reason=record.reason,
        operator=record.operator,
        created_at=record.created_at,
    )


def create_downtime(check_id: str, payload: CreateDowntimeRequest) -> CreateDowntimeResponse:
    if get_registered_command(check_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown check_id: {check_id}")

    record = persist_downtime(
        check_id=check_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        reason=payload.reason,
        operator=payload.operator,
    )
    return CreateDowntimeResponse(downtime=_downtime_entry_from_record(record))


def list_downtimes(check_id: str) -> ListDowntimesResponse:
    if get_registered_command(check_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown check_id: {check_id}")

    records = get_downtimes(check_id)
    return ListDowntimesResponse(
        downtimes=[_downtime_entry_from_record(record) for record in records]
    )
