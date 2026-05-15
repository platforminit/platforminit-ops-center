from fastapi import FastAPI

from app.api.checks import (
    RunCheckRequest,
    RunCheckResponse,
    run_check,
    ListChecksResponse,
    list_checks,
    RunRegisteredCheckRequest,
    RunRegisteredCheckResponse,
    run_registered_check,
)

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
