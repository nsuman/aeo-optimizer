"""Optimize API routes."""

from __future__ import annotations

import json
import logging
import traceback
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from google import genai

from app.config import get_settings
from app.errors import format_exception
from app.models.aeo import OptimizeResponse
from app.models.shopify import OptimizeRequest
from app.services.adk_runner import AdkOptimizeService, MissingApiKeyError

router = APIRouter(prefix="/v1", tags=["optimize"])
logger = logging.getLogger(__name__)

SAMPLE_CATALOG = Path(__file__).resolve().parents[2] / "samples" / "shopify_products.json"


@router.get("/sample")
async def sample_catalog() -> dict[str, Any]:
    if not SAMPLE_CATALOG.exists():
        raise HTTPException(status_code=404, detail="Sample catalog not found.")
    return json.loads(SAMPLE_CATALOG.read_text())


@router.get("/diagnose")
async def diagnose() -> dict[str, Any]:
    """Check env + a minimal Gemini call so Render failures are inspectable."""
    settings = get_settings()
    key = settings.resolved_google_api_key()
    result: dict[str, Any] = {
        "google_api_key_configured": bool(key),
        "google_api_key_suffix": key[-4:] if key and len(key) >= 4 else None,
        "model": settings.adk_model,
        "gemini_ok": False,
        "gemini_error": None,
        "gemini_text": None,
    }
    if not key:
        result["gemini_error"] = "GOOGLE_API_KEY is not set on this service."
        return result

    try:
        import os

        os.environ["GOOGLE_API_KEY"] = key
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=settings.adk_model,
            contents="Reply with exactly: ok",
        )
        text = getattr(response, "text", None) or ""
        result["gemini_ok"] = True
        result["gemini_text"] = text.strip()[:80]
    except Exception as exc:  # noqa: BLE001
        result["gemini_error"] = format_exception(exc)
        logger.exception("Gemini diagnose failed")
    return result


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
    except BaseExceptionGroup as exc:
        detail = format_exception(exc)
        logger.error("ADK TaskGroup failure:\n%s", traceback.format_exc())
        raise HTTPException(
            status_code=502,
            detail=f"ADK optimization failed: {detail}",
        ) from exc
    except Exception as exc:  # noqa: BLE001 — surface ADK/runtime errors to client
        detail = format_exception(exc)
        logger.error("ADK optimization failed:\n%s", traceback.format_exc())
        raise HTTPException(
            status_code=502,
            detail=f"ADK optimization failed: {detail}",
        ) from exc
