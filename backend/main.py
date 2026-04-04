from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.core.config import get_settings
from app.core.database import enable_pgvector, engine
from app.models import (
    User, Team, Coach, CoachStat,
    SeasonStat, SOSStat, TeamTrend, AICache,
)
from app.core.database import Base
from app.routers import auth, teams, stats, coaches, chat, admin

settings = get_settings()


# ── Startup / Shutdown ────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    enable_pgvector()
    Base.metadata.create_all(bind=engine)
    print("✓ pgvector enabled")
    yield
    # Runs once on shutdown — nothing to clean up


# ── App factory ───────────────────────────────────────────────
app = FastAPI(
    title       = "Playbook Football API",
    description = "NFL and CFB stats, trends, and AI chatbot",
    version     = "1.0.0",
    lifespan    = lifespan,
    docs_url    = "/api/docs" if settings.debug else None,
    redoc_url   = None,
)


# ── CORS ──────────────────────────────────────────────────────
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins     = origins,
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ── Routers ───────────────────────────────────────────────────
app.include_router(auth.router,    prefix="/api/auth",    tags=["auth"])
app.include_router(teams.router,   prefix="/api/teams",   tags=["teams"])
app.include_router(stats.router,   prefix="/api/stats",   tags=["stats"])
app.include_router(coaches.router, prefix="/api/coaches", tags=["coaches"])
app.include_router(chat.router,    prefix="/api/chat",    tags=["chat"])
app.include_router(admin.router,   prefix="/api/admin",   tags=["admin"])


# ── Health check ──────────────────────────────────────────────
@app.get("/api/health", tags=["health"])
async def health():
    return {
        "status": "ok",
        "env"   : settings.app_env,
    }


# ── Serve React in production ─────────────────────────────────
# In development Vite runs on port 5173
# In production FastAPI serves the built React files
if not settings.debug:
    frontend_dist = os.path.join(
        os.path.dirname(__file__),
        "../frontend/dist"
    )
    if os.path.exists(frontend_dist):
        app.mount(
            "/assets",
            StaticFiles(directory=f"{frontend_dist}/assets"),
            name="assets",
        )

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_react(full_path: str):
            return FileResponse(f"{frontend_dist}/index.html")

