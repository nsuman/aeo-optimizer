"""Per-product AEO LlmAgent factory."""

from __future__ import annotations

import json
from typing import Any

from google.adk.agents import LlmAgent

from app.agents.prompts import PRODUCT_AEO_INSTRUCTION
from app.models.aeo import AeoProductDiff


def create_product_agent(
    *,
    name: str,
    model: str,
    product: dict[str, Any],
    output_key: str,
) -> LlmAgent:
    """Build an LlmAgent scoped to a single Shopify product node."""
    product_json = json.dumps(product, ensure_ascii=False, indent=2)
    instruction = (
        f"{PRODUCT_AEO_INSTRUCTION}\n\n"
        f"## Product to optimize\n"
        f"```json\n{product_json}\n```"
    )
    return LlmAgent(
        name=name,
        model=model,
        description=(
            "Scores one Shopify product for agentic selectability and "
            "returns structured AEO patches."
        ),
        instruction=instruction,
        output_schema=AeoProductDiff,
        output_key=output_key,
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )
