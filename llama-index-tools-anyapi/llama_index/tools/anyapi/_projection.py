"""Token-light projections of AnyAPI catalog and run models, for llama-index.

Every value here is read from a ``getanyapi`` model exactly as the gateway
published it. Prices are never scaled: ``maxUsd`` is what one request is
billed and ``maxPer1kUsd`` is the same maximum per 1,000 requests, and both
come off the wire. ``provider`` is always ``AnyAPI``; the SDK rejects any
discovery body that says otherwise before these functions ever see it.
"""

from __future__ import annotations

from typing import Any

from getanyapi import (
    AnyAPIError,
    CatalogEntry,
    CatalogSearchResult,
    DiscoveryPricing,
    OutputFound,
    PricingOffer,
    RunResult,
)


def offer_dict(offer: PricingOffer) -> dict[str, Any]:
    """One published USD offer, in both denominations, unscaled."""
    out: dict[str, Any] = {
        "model": offer.model,
        "unit": offer.unit,
        "maxUsd": offer.max_usd,
        "maxPer1kUsd": offer.max_per1k_usd,
    }
    if offer.model == "linear":
        out["baseUsd"] = offer.base_usd
        out["perUnitUsd"] = offer.per_unit_usd
    return out


def pricing_dict(pricing: DiscoveryPricing) -> dict[str, Any]:
    """The cheapest offer plus the failover ceiling, in both denominations."""
    return {
        "from": offer_dict(pricing.from_offer),
        "failoverMaxUsd": pricing.failover_max_usd,
        "failoverMaxPer1kUsd": pricing.failover_max_per1k_usd,
    }


def summary_dict(entry: CatalogEntry) -> dict[str, Any]:
    """A browse-weight summary: no description, no schemas."""
    return {
        "id": entry.slug,
        "name": entry.name,
        "category": entry.category,
        "pricing": pricing_dict(entry.pricing),
        "heavy": entry.heavy,
        "execution": entry.execution.mode,
    }


def detail_dict(entry: CatalogEntry) -> dict[str, Any]:
    """The full definition of one API, including its strict input schema."""
    out = summary_dict(entry)
    out.update(
        {
            "description": entry.description,
            "provider": entry.provider,
            "method": entry.method,
            "path": entry.path,
            "inputSchema": entry.input_schema,
            "outputSchema": entry.output_schema,
            "lanes": [
                {"pricing": offer_dict(lane.pricing), "source": lane.source.name}
                for lane in entry.lanes
            ],
        }
    )
    if entry.latency is not None:
        out["latency"] = {
            "window": entry.latency.window,
            "p50Ms": entry.latency.p50_ms,
            "p95Ms": entry.latency.p95_ms,
            "p99Ms": entry.latency.p99_ms,
            "sample": entry.latency.sample,
        }
    else:
        out["latency"] = None
    return out


def search_dict(result: CatalogSearchResult) -> dict[str, Any]:
    """One ranked search match: description kept, schemas omitted."""
    return {
        "id": result.slug,
        "platform": result.platform_id,
        "name": result.name,
        "description": result.description,
        "category": result.category,
        "pricing": pricing_dict(result.pricing),
        "execution": result.execution.mode,
        "relevance": result.relevance,
    }


def run_dict(result: RunResult[Any]) -> dict[str, Any]:
    """The billed run envelope, with the found/not-found branch flattened."""
    found = isinstance(result.output, OutputFound)
    return {
        "found": found,
        "data": result.output.data if isinstance(result.output, OutputFound) else None,
        "provider": result.provider,
        "costUsd": result.cost_usd,
        "items": result.items,
        "resultId": result.result_id,
    }


def error_dict(exc: AnyAPIError) -> dict[str, Any]:
    """A readable, recoverable error payload rather than a raised exception.

    The MCP server answers a failed tool call with text the model can act on
    instead of aborting the run, and these tools follow it. ``code`` is the
    stable gateway error code when the body carried one.
    """
    payload: dict[str, Any] = {"error": str(exc), "status": exc.status}
    if exc.code:
        payload["code"] = exc.code
    if exc.request_id:
        payload["requestId"] = exc.request_id
    return payload
