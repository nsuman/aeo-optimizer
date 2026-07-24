"""AEO diff / patch response models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AeoFinding(BaseModel):
    severity: Literal["low", "medium", "high"]
    code: str = Field(
        description="Stable finding code, e.g. missing_audience, vague_title"
    )
    message: str


class AeoPatch(BaseModel):
    path: str = Field(
        description="JSON Pointer against the product object, e.g. /title"
    )
    op: Literal["replace", "add", "remove"] = "replace"
    before: Any = None
    after: Any = None
    rationale: str


class AeoProductDiff(BaseModel):
    product_id: str
    score_before: int = Field(ge=0, le=100)
    score_after: int = Field(ge=0, le=100)
    findings: list[AeoFinding] = Field(default_factory=list)
    patches: list[AeoPatch] = Field(default_factory=list)


class OptimizeResponse(BaseModel):
    products: list[AeoProductDiff] = Field(default_factory=list)
