from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents import registry as _registry  # noqa: F401  (registers blueprints)
from app.config import settings
from app.curator import ensure_curated
from app.db import SessionLocal, init_db
from app.governance import seed_defaults
from app.routers import (
    admin,
    blueprints,
    catalog,
    chat,
    conversations,
    faces,
    models,
    route,
    runs,
    usage,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as db:
        seed_defaults(db)
    ensure_curated()
    yield


app = FastAPI(title=settings.app_name, version="0.6.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(models.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(usage.router)
app.include_router(route.router)
app.include_router(admin.router)
app.include_router(admin.alerts_router)
app.include_router(blueprints.router)
app.include_router(blueprints.data_router)
app.include_router(runs.router)
app.include_router(catalog.router)
app.include_router(faces.router)


@app.get("/health")
def health() -> dict[str, str | bool]:
    """Liveness probe used by the web app, Playwright, and Container Apps."""
    return {"status": "ok", "environment": settings.environment, "fake_llm": settings.fake_llm}


@app.get("/v1/meta")
def meta() -> dict[str, object]:
    return {
        "app": settings.app_name,
        "version": app.version,
        "batch": 5,
        "sections": ["home", "discover", "build", "evaluate", "operate", "community", "admin"],
    }
