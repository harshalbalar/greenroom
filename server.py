"""
Greenroom API server.

Run: uvicorn server:app --reload --port 8000
Docs: http://localhost:8000/docs (Swagger UI)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    version="0.4.0",
    lifespan=lifespan,
)

# CORS — allow React frontend (Phase 5) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all route modules
app.include_router(auth.router)
app.include_router(resumes.router)
app.include_router(preferences.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(events.router)


@app.get("/")
def root():
    return {
        "name": "Greenroom",
        "tagline": "Your applications, prepped and ready.",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
