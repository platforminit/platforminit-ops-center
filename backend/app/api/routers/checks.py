"""Checks, problems, scheduler, and operator-action router.

Preserves all existing OpenAPI paths, auth guards, and redaction behaviour.
"""

from fastapi import APIRouter, Depends, Query

from app.api.checks import (
    AcknowledgeRequest,
    AcknowledgeResponse,
    CheckHistoryResponse,
    CommentRequest,
    CommentResponse,
    CreateDowntimeRequest,
    CreateDowntimeResponse,
    LatestResultsResponse,
    ListDowntimesResponse,
    ListChecksResponse,
    ProblemsResponse,
    RunCheckRequest,
    RunCheckResponse,
    RunRegisteredCheckRequest,
    RunRegisteredCheckResponse,
    SchedulerRunResponse,
    acknowledge_check,
    add_comment,
    check_history,
    create_downtime,
    latest_results,
    list_checks,
    list_downtimes,
    list_problems,
    run_check,
    run_registered_check,
    run_scheduler,
)
from app.core.security import require_auth
from app.store.check_results import DEFAULT_HISTORY_LIMIT, MAX_HISTORY_LIMIT

router = APIRouter(prefix="/api/v1", tags=["checks"])


# ---------------------------------------------------------------------------
# Read-only endpoints — no auth required (MVP)
# ---------------------------------------------------------------------------


@router.get("/checks", response_model=ListChecksResponse)
def checks_list() -> ListChecksResponse:
    return list_checks()


@router.get("/checks/{check_id}/history", response_model=CheckHistoryResponse)
def checks_history(
    check_id: str,
    limit: int = Query(default=DEFAULT_HISTORY_LIMIT, ge=1, le=MAX_HISTORY_LIMIT),
) -> CheckHistoryResponse:
    return check_history(check_id, limit=limit)


@router.get("/results/latest", response_model=LatestResultsResponse)
def results_latest() -> LatestResultsResponse:
    return latest_results()


@router.get("/problems", response_model=ProblemsResponse)
def problems_list() -> ProblemsResponse:
    return list_problems()


@router.get("/checks/{check_id}/downtimes", response_model=ListDowntimesResponse)
def checks_list_downtimes(
    check_id: str,
) -> ListDowntimesResponse:
    return list_downtimes(check_id)


# ---------------------------------------------------------------------------
# Mutation endpoints — auth required (when OPS_CENTER_AUTH_ENABLED=true)
# ---------------------------------------------------------------------------


@router.post("/checks/run", dependencies=[Depends(require_auth)])
def checks_run(payload: RunCheckRequest) -> RunCheckResponse:
    return run_check(payload)


@router.post("/checks/{check_id}/run", dependencies=[Depends(require_auth)])
def checks_run_registered(
    check_id: str, payload: RunRegisteredCheckRequest
) -> RunRegisteredCheckResponse:
    return run_registered_check(check_id, payload)


@router.post("/scheduler/run", dependencies=[Depends(require_auth)])
def scheduler_run() -> SchedulerRunResponse:
    return run_scheduler()


@router.post("/checks/{check_id}/acknowledge", dependencies=[Depends(require_auth)])
def checks_acknowledge(
    check_id: str, payload: AcknowledgeRequest
) -> AcknowledgeResponse:
    return acknowledge_check(check_id, payload)


@router.post("/checks/{check_id}/comments", dependencies=[Depends(require_auth)])
def checks_comments(
    check_id: str, payload: CommentRequest
) -> CommentResponse:
    return add_comment(check_id, payload)


@router.post("/checks/{check_id}/downtimes", dependencies=[Depends(require_auth)])
def checks_create_downtime(
    check_id: str, payload: CreateDowntimeRequest
) -> CreateDowntimeResponse:
    return create_downtime(check_id, payload)
