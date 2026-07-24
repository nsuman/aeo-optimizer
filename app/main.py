"""FastAPI entrypoint for the AEO optimizer."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.optimize import router as optimize_router

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
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
