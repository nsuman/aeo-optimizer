"""Optimize API routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.models.aeo import OptimizeResponse
from app.models.shopify import OptimizeRequest
from app.services.adk_runner import AdkOptimizeService, MissingApiKeyError

router = APIRouter(prefix="/v1", tags=["optimize"])

SAMPLE_CATALOG = Path(__file__).resolve().parents[2] / "samples" / "shopify_products.json"


def _format_exception(exc: BaseException) -> str:
    if isinstance(exc, BaseExceptionGroup):
        parts = [_format_exception(child) for child in exc.exceptions]
        return "; ".join(parts)
    message = str(exc).strip()
    return message or type(exc).__name__


@router.get("/sample")
async def sample_catalog() -> dict[str, Any]:
    if not SAMPLE_CATALOG.exists():
        raise HTTPException(status_code=404, detail="Sample catalog not found.")
    return json.loads(SAMPLE_CATALOG.read_text())


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_catalog(body: OptimizeRequest) -> OptimizeResponse:
    settings = get_settings()
    products = body.product_list()

    if not products:
        raise HTTPException(status_code=422, detail="No products provided.")

    if len(products) > settings.max_products:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Too many products: {len(products)}. "
                f"MAX_PRODUCTS={settings.max_products}."
            ),
        )

    service = AdkOptimizeService(settings)
    try:
        return await service.optimize(products)
    except MissingApiKeyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface ADK/runtime errors to client
        raise HTTPException(
            status_code=502,
            detail=f"ADK optimization failed: {_format_exception(exc)}",
        ) from exc
