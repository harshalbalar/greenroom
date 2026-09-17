"""
Greenroom API server.

Run locally:  uvicorn server:app --reload --port 8000
Production:   gunicorn server:app -w 2 -k uvicorn.workers.UvicornWorker

In production, FastAPI serves the React build from frontend/dist/
so everything runs on a single domain — no CORS issues.
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import init_db
from routes import auth, resumes, preferences
from routes import jobs_v2 as jobs
from routes import applications_v2 as applications
from routes import events


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup."""
    init_db()
    print("  Greenroom API ready.")
    yield


app = FastAPI(
    title="Greenroom API",
    description="Your applications, prepped and ready.",
    version="0.5.0",
    lifespan=lifespan,
)

# CORS — needed for local dev (Vite proxy handles most of it,
# but SSE connections bypass the proxy). In production, frontend
# is served from the same origin so CORS isn't needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all API route modules
app.include_router(auth.router)
app.include_router(resumes.router)
app.include_router(preferences.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(events.router)


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Serve React frontend in production ────────────────────────────────
# If frontend/dist exists (i.e. the React app was built), serve it.
# All non-API routes fall through to index.html (React Router handles them).

FRONTEND_DIR = Path(__file__).parent / "frontend" / "dist"

if FRONTEND_DIR.is_dir():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="static")

    # Catch-all: serve index.html for any non-API route (React Router)
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Don't intercept API routes or docs
        if full_path.startswith("api/") or full_path in ("docs", "redoc", "openapi.json"):
            return  # Let FastAPI handle it
        # Serve the actual file if it exists (favicon.ico, etc.)
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        # Everything else → index.html (React Router takes over)
        return FileResponse(FRONTEND_DIR / "index.html")
else:
    # No build yet — show API info on root
    @app.get("/")
    def root():
        return {
            "name": "Greenroom",
            "tagline": "Your applications, prepped and ready.",
            "docs": "/docs",
        }