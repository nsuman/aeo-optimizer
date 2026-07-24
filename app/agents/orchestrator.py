"""Orchestrator that runs one product AEO agent per catalog item (sequential)."""

from __future__ import annotations

from typing import Any, AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types
from pydantic import Field
from typing_extensions import override

from app.agents.product_agent import create_product_agent
from app.models.aeo import AeoProductDiff


def _sanitize_agent_name(_product_id: str, index: int) -> str:
    """ADK agent names must be valid identifiers; avoid Shopify GID punctuation."""
    return f"product_aeo_{index}"


def _coerce_diff(raw: Any, product_id: str) -> dict[str, Any]:
    if raw is None:
        return AeoProductDiff(
            product_id=product_id,
            score_before=0,
            score_after=0,
            findings=[],
            patches=[],
        ).model_dump()
    if isinstance(raw, AeoProductDiff):
        return raw.model_dump()
    if isinstance(raw, dict):
        try:
            return AeoProductDiff.model_validate(raw).model_dump()
        except Exception:
            fallback = dict(raw)
            fallback.setdefault("product_id", product_id)
            return fallback
    return AeoProductDiff(
        product_id=product_id,
        score_before=0,
        score_after=0,
        findings=[],
        patches=[],
    ).model_dump()


class AeoOrchestratorAgent(BaseAgent):
    """Read products from session state, run product agents sequentially, aggregate."""

    model: str = Field(default="gemini-2.5-flash")
    """Gemini model id passed through to each product agent."""

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        products = ctx.session.state.get("products") or []
        if not isinstance(products, list):
            products = []

        if not products:
            report = {"products": []}
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text="No products to optimize.")],
                ),
                actions=EventActions(state_delta={"aeo_report": report}),
            )
            return

        sub_agents = []
        output_keys: list[tuple[str, str]] = []
        for index, product in enumerate(products):
            if not isinstance(product, dict):
                continue
            product_id = str(product.get("id", f"unknown_{index}"))
            agent_name = _sanitize_agent_name(product_id, index)
            output_key = f"aeo_diff_{index}"
            output_keys.append((output_key, product_id))
            sub_agents.append(
                create_product_agent(
                    name=agent_name,
                    model=self.model,
                    product=product,
                    output_key=output_key,
                )
            )

        if not sub_agents:
            report = {"products": []}
            yield Event(
                author=self.name,
                actions=EventActions(state_delta={"aeo_report": report}),
            )
            return

        # Sequential only — ParallelAgent wraps failures in opaque TaskGroup errors
        # and OOMs easily on Render free instances.
        for agent in sub_agents:
            async for event in agent.run_async(ctx):
                yield event

        diffs: list[dict[str, Any]] = []
        for output_key, product_id in output_keys:
            raw = ctx.session.state.get(output_key)
            diffs.append(_coerce_diff(raw, product_id))

        report = {"products": diffs}
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text=f"AEO optimization complete for {len(diffs)} product(s)."
                    )
                ],
            ),
            actions=EventActions(state_delta={"aeo_report": report}),
        )


def build_root_agent(model: str, *, parallel: bool = False) -> AeoOrchestratorAgent:
    del parallel  # kept for call-site compatibility; parallel fan-out removed
    return AeoOrchestratorAgent(
        name="aeo_orchestrator",
        description=(
            "Orchestrates per-product AEO agents over a Shopify catalog "
            "and aggregates structured diffs."
        ),
        model=model,
    )
