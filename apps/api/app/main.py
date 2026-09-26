from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adoption import ensure_assumptions
from app.agents import registry as _registry  # noqa: F401  (registers blueprints)
from app.config import settings
from app.connectors import seed_connectors
from app.curator import ensure_curated
from app.db import SessionLocal, init_db
from app.evals import ensure_system_suites, start_scheduler
from app.governance import seed_defaults
from app.routers import (
    admin,
    adoption,
    blueprints,
    catalog,
    chat,
    community,
    connectors,
    conversations,
    evals,
    faces,
    knowledge,
    mcp,
    models,
    route,
    runs,
    skills,
    usage,
)
from app.security import RateLimitMiddleware, SecurityHeadersMiddleware, assert_safe_configuration


@asynccontextmanager
async def lifespan(_: FastAPI):
    assert_safe_configuration()  # refuses to start with development defaults outside local environments
    init_db()
    with SessionLocal() as db:
        seed_defaults(db)
        seed_connectors(db)
        ensure_system_suites(db)
        ensure_assumptions(db)
    ensure_curated()
    start_scheduler()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
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
app.include_router(connectors.router)
app.include_router(knowledge.router)
app.include_router(skills.router)
app.include_router(mcp.router)
app.include_router(evals.router)
app.include_router(community.router)
app.include_router(adoption.router)


@app.get("/health")
def health() -> dict[str, str | bool]:
    """Liveness probe used by the web app, Playwright, and Container Apps."""
    return {"status": "ok", "environment": settings.environment, "fake_llm": settings.fake_llm}


@app.get("/v1/meta")
def meta() -> dict[str, object]:
    return {
        "app": settings.app_name,
        "version": app.version,
        "batch": 9,
        "sections": ["home", "discover", "build", "evaluate", "operate", "community", "admin"],
    }
