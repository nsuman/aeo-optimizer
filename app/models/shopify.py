"""Pydantic models for a Shopify Admin GraphQL products connection subset."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ShopifyModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class SeoIn(ShopifyModel):
    title: str | None = None
    description: str | None = None


class VariantIn(ShopifyModel):
    id: str
    title: str | None = None
    sku: str | None = None
    price: str | None = None
    available_for_sale: bool | None = Field(
        default=None, alias="availableForSale"
    )

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class VariantConnectionIn(ShopifyModel):
    nodes: list[VariantIn] = Field(default_factory=list)


class ProductIn(ShopifyModel):
    id: str
    title: str | None = None
    description: str | None = None
    description_html: str | None = Field(default=None, alias="descriptionHtml")
    vendor: str | None = None
    product_type: str | None = Field(default=None, alias="productType")
    tags: list[str] = Field(default_factory=list)
    seo: SeoIn | None = None
    variants: VariantConnectionIn | list[VariantIn] | None = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    def variant_nodes(self) -> list[VariantIn]:
        if self.variants is None:
            return []
        if isinstance(self.variants, list):
            return self.variants
        return self.variants.nodes


class ProductConnectionIn(ShopifyModel):
    nodes: list[ProductIn] = Field(default_factory=list)


class OptimizeRequest(ShopifyModel):
    """Accepts Shopify GraphQL `products` shape or a flat product list."""

    products: ProductConnectionIn | list[ProductIn] | dict[str, Any]

    @model_validator(mode="after")
    def _normalize_products(self) -> OptimizeRequest:
        raw = self.products
        if isinstance(raw, list):
            self.products = ProductConnectionIn(nodes=raw)
        elif isinstance(raw, dict):
            if "nodes" in raw:
                self.products = ProductConnectionIn.model_validate(raw)
            elif "edges" in raw:
                nodes = [
                    ProductIn.model_validate(edge.get("node", edge))
                    for edge in raw["edges"]
                ]
                self.products = ProductConnectionIn(nodes=nodes)
            else:
                raise ValueError(
                    "products must be a connection with nodes/edges or a list"
                )
        return self

    def product_list(self) -> list[ProductIn]:
        assert isinstance(self.products, ProductConnectionIn)
        return self.products.nodes
