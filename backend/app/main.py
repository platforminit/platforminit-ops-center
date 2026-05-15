from fastapi import FastAPI

app = FastAPI(title="PlatformInit Ops Center API")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
