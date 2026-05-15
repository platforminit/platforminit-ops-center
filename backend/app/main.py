from fastapi import FastAPI

from app.api.checks import RunCheckRequest, RunCheckResponse, run_check

app = FastAPI(title="PlatformInit Ops Center API")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/checks/run")
def checks_run(payload: RunCheckRequest) -> RunCheckResponse:
    return run_check(payload)
