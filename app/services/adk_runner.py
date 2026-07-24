"""ADK Runner wrapper: seed catalog state, run orchestrator, return AEO report."""

from __future__ import annotations

import os
import uuid
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agents.orchestrator import build_root_agent
from app.config import Settings, get_settings
from app.models.aeo import AeoProductDiff, OptimizeResponse
from app.models.shopify import ProductIn


class MissingApiKeyError(RuntimeError):
    """Raised when Gemini credentials are not configured."""


def _product_to_state_dict(product: ProductIn) -> dict[str, Any]:
    return product.model_dump(by_alias=True, exclude_none=False)


class AdkOptimizeService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _ensure_api_key(self) -> str:
        key = self.settings.resolved_google_api_key()
        if not key:
            raise MissingApiKeyError(
                "GOOGLE_API_KEY is not set. In Render: Dashboard → Environment → "
                "add GOOGLE_API_KEY, then redeploy."
            )
        os.environ["GOOGLE_API_KEY"] = key
        os.environ.setdefault("GEMINI_API_KEY", key)
        return key

    async def optimize(self, products: list[ProductIn]) -> OptimizeResponse:
        self._ensure_api_key()

        app_name = self.settings.app_name
        user_id = "api"
        session_id = str(uuid.uuid4())
        product_payloads = [_product_to_state_dict(p) for p in products]

        session_service = InMemorySessionService()
        await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            state={"products": product_payloads},
        )

        root_agent = build_root_agent(self.settings.adk_model)
        runner = Runner(
            agent=root_agent,
            app_name=app_name,
            session_service=session_service,
        )

        message = types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=(
                        f"Optimize {len(product_payloads)} Shopify product(s) "
                        "for Agentic Engine Optimization. Fan out one product "
                        "agent per item and aggregate AEO diffs into aeo_report."
                    )
                )
            ],
        )

        async for _event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message,
        ):
            pass

        session = await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
        )
        report = (session.state if session else {}).get("aeo_report") or {}
        raw_products = report.get("products") if isinstance(report, dict) else []
        if not isinstance(raw_products, list):
            raw_products = []

        diffs: list[AeoProductDiff] = []
        for item in raw_products:
            try:
                diffs.append(AeoProductDiff.model_validate(item))
            except Exception:
                continue

        # If aggregation missed some agents, fall back to per-key outputs.
        if not diffs:
            state = session.state if session else {}
            for index, product in enumerate(product_payloads):
                key = f"aeo_diff_{index}"
                raw = state.get(key)
                if raw is None:
                    continue
                try:
                    diffs.append(AeoProductDiff.model_validate(raw))
                except Exception:
                    continue

        return OptimizeResponse(products=diffs)
