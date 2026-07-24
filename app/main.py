"""FastAPI entrypoint for the AEO optimizer."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.optimize import router as optimize_router
from app.config import get_settings

# Slim Docker images often lack MIME mappings, so browsers reject CSS/JS as text/plain.
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("image/png", ".png")
mimetypes.add_type("image/webp", ".webp")

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="AEO Optimizer",
    description=(
        "Accepts Shopify GraphQL catalog JSON and returns Agentic Engine "
        "Optimization diffs via Google ADK multi-agent fan-out."
    ),
    version="0.1.0",
)

app.include_router(optimize_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
async def health() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": "ok",
        "google_api_key_configured": bool(settings.resolved_google_api_key()),
        "model": settings.adk_model,
    }


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")
