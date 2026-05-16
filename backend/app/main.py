from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

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
    ProblemsResponse,
    RunCheckRequest,
    RunCheckResponse,
    ListChecksResponse,
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
from app.api.inventory import (
    ListHostsResponse,
    ListServicesResponse,
    list_hosts_handler,
    list_services_handler,
)
from app.core.security import require_auth
from app.store.check_results import DEFAULT_HISTORY_LIMIT, MAX_HISTORY_LIMIT

app = FastAPI(title="PlatformInit Ops Center API")

# ---------------------------------------------------------------------------
# CORS — restrict origins in production
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)


# ---------------------------------------------------------------------------
# Health / read-only endpoints — no auth required (MVP)
# ---------------------------------------------------------------------------


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/checks", response_model=ListChecksResponse)
def checks_list() -> ListChecksResponse:
    return list_checks()


@app.get("/api/v1/checks/{check_id}/history", response_model=CheckHistoryResponse)
def checks_history(
    check_id: str,
    limit: int = Query(default=DEFAULT_HISTORY_LIMIT, ge=1, le=MAX_HISTORY_LIMIT),
) -> CheckHistoryResponse:
    return check_history(check_id, limit=limit)


@app.get("/api/v1/results/latest", response_model=LatestResultsResponse)
def results_latest() -> LatestResultsResponse:
    return latest_results()


@app.get("/api/v1/problems", response_model=ProblemsResponse)
def problems_list() -> ProblemsResponse:
    return list_problems()


@app.get("/api/v1/hosts", response_model=ListHostsResponse)
def hosts_list() -> ListHostsResponse:
    return list_hosts_handler()


@app.get("/api/v1/services", response_model=ListServicesResponse)
def services_list() -> ListServicesResponse:
    return list_services_handler()


@app.get("/api/v1/checks/{check_id}/downtimes", response_model=ListDowntimesResponse)
def checks_list_downtimes(
    check_id: str,
) -> ListDowntimesResponse:
    return list_downtimes(check_id)


# ---------------------------------------------------------------------------
# Mutation endpoints — auth required (when OPS_CENTER_AUTH_ENABLED=true)
# ---------------------------------------------------------------------------


@app.post("/api/v1/checks/run", dependencies=[Depends(require_auth)])
def checks_run(payload: RunCheckRequest) -> RunCheckResponse:
    return run_check(payload)


@app.post("/api/v1/checks/{check_id}/run", dependencies=[Depends(require_auth)])
def checks_run_registered(
    check_id: str, payload: RunRegisteredCheckRequest
) -> RunRegisteredCheckResponse:
    return run_registered_check(check_id, payload)


@app.post("/api/v1/scheduler/run", dependencies=[Depends(require_auth)])
def scheduler_run() -> SchedulerRunResponse:
    return run_scheduler()


@app.post("/api/v1/checks/{check_id}/acknowledge", dependencies=[Depends(require_auth)])
def checks_acknowledge(
    check_id: str, payload: AcknowledgeRequest
) -> AcknowledgeResponse:
    return acknowledge_check(check_id, payload)


@app.post("/api/v1/checks/{check_id}/comments", dependencies=[Depends(require_auth)])
def checks_comments(
    check_id: str, payload: CommentRequest
) -> CommentResponse:
    return add_comment(check_id, payload)


@app.post("/api/v1/checks/{check_id}/downtimes", dependencies=[Depends(require_auth)])
def checks_create_downtime(
    check_id: str, payload: CreateDowntimeRequest
) -> CreateDowntimeResponse:
    return create_downtime(check_id, payload)
