from fastapi import FastAPI, Query

from app.api.checks import (
    CheckHistoryResponse,
    LatestResultsResponse,
    ProblemsResponse,
    RunCheckRequest,
    RunCheckResponse,
    ListChecksResponse,
    RunRegisteredCheckRequest,
    RunRegisteredCheckResponse,
    check_history,
    latest_results,
    list_checks,
    list_problems,
    run_check,
    run_registered_check,
)
from app.store.check_results import DEFAULT_HISTORY_LIMIT, MAX_HISTORY_LIMIT

app = FastAPI(title="PlatformInit Ops Center API")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/checks/run")
def checks_run(payload: RunCheckRequest) -> RunCheckResponse:
    return run_check(payload)


@app.get("/api/v1/checks", response_model=ListChecksResponse)
def checks_list() -> ListChecksResponse:
    return list_checks()


@app.post("/api/v1/checks/{check_id}/run", response_model=RunRegisteredCheckResponse)
def checks_run_registered(
    check_id: str, payload: RunRegisteredCheckRequest
) -> RunRegisteredCheckResponse:
    return run_registered_check(check_id, payload)


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
