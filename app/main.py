"""Deadline Necromancer — FastAPI application entry point.

API routes are registered before the static mount so `/api/*` always wins
over the frontend catch-all.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api.routes import router

app = FastAPI(
    title="Deadline Necromancer",
    description="An AI that resurrects your abandoned projects — locally, with Gemma.",
    version="1.0.0",
)

app.include_router(router)

_static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
