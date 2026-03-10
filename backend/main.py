"""
TechHub Customer Support — FastAPI backend entry point.

Run locally:
    uv run uvicorn backend.main:app --reload --port 8000

API docs available at:
    http://localhost:8000/docs
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.chat import router as chat_router
from backend.api.routes.sessions import router as sessions_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="TechHub Customer Support API",
    description="AI-powered customer support agent backed by LangGraph",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS — allow the frontend dev server (adjust origins in production)
# ---------------------------------------------------------------------------
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173",  # Next.js / Vite defaults
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(chat_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}
