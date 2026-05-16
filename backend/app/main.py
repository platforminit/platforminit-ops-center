from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.checks import router as checks_router
from app.api.routers.health import router as health_router
from app.api.routers.inventory import router as inventory_router

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
# Domain routers
# ---------------------------------------------------------------------------
app.include_router(health_router)
app.include_router(checks_router)
app.include_router(inventory_router)
