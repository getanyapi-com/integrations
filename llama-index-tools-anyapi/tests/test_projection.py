"""What the tools emit: USD only, provider AnyAPI, and prices read through."""

from __future__ import annotations

import json
from typing import Any

from getanyapi import AnyAPIError, CatalogEntry, CatalogSearchResults, RunResult

from llama_index.tools.anyapi._projection import (
    detail_dict,
    error_dict,
    run_dict,
    search_dict,
    summary_dict,
)


def test_summary_is_browse_weight(entry: CatalogEntry) -> None:
    out = summary_dict(entry)
    assert out["id"] == "reddit.trending_posts"
    assert out["execution"] == "sync"
    assert "description" not in out
    assert "inputSchema" not in out


def test_detail_carries_the_strict_input_schema(entry: CatalogEntry) -> None:
    out = detail_dict(entry)
    assert out["inputSchema"]["additionalProperties"] is False
    assert out["latency"]["p95Ms"] == 2100
    assert out["lanes"] == [
        {
            "pricing": {
                "model": "flat",
                "unit": "request",
                "maxUsd": 0.00036,
                "maxPer1kUsd": 0.36,
            },
            "source": "Badger",
        }
    ]


def test_provider_is_always_anyapi(
    entry: CatalogEntry, run_result: RunResult[Any]
) -> None:
    assert detail_dict(entry)["provider"] == "AnyAPI"
    assert run_dict(run_result)["provider"] == "AnyAPI"


def test_no_output_field_mentions_credits(
    entry: CatalogEntry,
    run_result: RunResult[Any],
    search_results: CatalogSearchResults,
) -> None:
    payloads = [
        detail_dict(entry),
        summary_dict(entry),
        run_dict(run_result),
        search_dict(search_results.results[0]),
    ]
    for payload in payloads:
        for key in _all_keys(payload):
            assert "credit" not in key.lower(), key


def _all_keys(value: Any) -> list[str]:
    if isinstance(value, dict):
        keys: list[str] = []
        for key, child in value.items():
            keys.append(str(key))
            keys.extend(_all_keys(child))
        return keys
    if isinstance(value, list):
        return [k for item in value for k in _all_keys(item)]
    return []


def test_a_price_is_never_scaled(entry: CatalogEntry) -> None:
    """Both denominations come off the wire; neither is derived from the other."""
    published = entry.pricing.from_offer
    out = detail_dict(entry)["pricing"]
    assert out["from"]["maxUsd"] == published.max_usd
    assert out["from"]["maxPer1kUsd"] == published.max_per1k_usd
    assert out["failoverMaxUsd"] == entry.pricing.failover_max_usd
    assert out["failoverMaxPer1kUsd"] == entry.pricing.failover_max_per1k_usd
    # A scaled figure would be 0.36000000000000004, not the published 0.36.
    assert out["from"]["maxPer1kUsd"] != published.max_usd * 1000


def test_run_result_reports_the_actual_cost(run_result: RunResult[Any]) -> None:
    out = run_dict(run_result)
    assert out == {
        "found": True,
        "data": {"posts": [{"title": "hello"}]},
        "provider": "AnyAPI",
        "costUsd": 0.00036,
        "items": 2,
        "resultId": "req_abc123",
    }
    assert "costPer1kUsd" not in json.dumps(out)


def test_not_found_run_flattens_to_a_null_payload() -> None:
    result = RunResult[Any].model_validate(
        {
            "output": {"found": False, "data": None},
            "provider": "AnyAPI",
            "costUsd": 0.0,
            "items": 0,
            "replayed": False,
        }
    )
    out = run_dict(result)
    assert out["found"] is False
    assert out["data"] is None


def test_search_keeps_descriptions_and_drops_schemas(
    search_results: CatalogSearchResults,
) -> None:
    out = search_dict(search_results.results[0])
    assert out["description"] == "Trending posts across Reddit."
    assert out["relevance"] == 1.0
    assert "inputSchema" not in out


def test_error_dict_is_a_payload_not_an_exception() -> None:
    exc = AnyAPIError("nope", status=402, code="insufficient_balance", request_id="r_1")
    assert error_dict(exc) == {
        "error": "nope",
        "status": 402,
        "code": "insufficient_balance",
        "requestId": "r_1",
    }
