"""The projections carry the gateway's own USD figures, unscaled."""

from __future__ import annotations

from typing import Any

from langchain_anyapi._projection import (
    detail_dict,
    error_dict,
    run_dict,
    search_dict,
    summary_dict,
)

from .fakes import catalog_entry, run_result, search_results
from .helpers import every_key, failing_error


def test_summary_is_browse_weight() -> None:
    """A summary carries pricing but neither description nor schemas."""
    out = summary_dict(catalog_entry())
    assert out["id"] == "reddit.trending_posts"
    assert out["category"] == "social"
    assert out["execution"] == "sync"
    assert "description" not in out
    assert "inputSchema" not in out


def test_detail_carries_the_strict_input_schema() -> None:
    """get_api is the only place an agent can read the input schema."""
    out = detail_dict(catalog_entry())
    assert out["inputSchema"]["additionalProperties"] is False
    assert out["outputSchema"] == {"type": "object"}
    assert out["latency"]["p99Ms"] == 8900
    assert out["lanes"] == [
        {
            "pricing": {
                "model": "flat",
                "unit": "request",
                "maxUsd": 0.00036,
                "maxPer1kUsd": 0.3,
            },
            "source": "Badger",
        }
    ]


def test_search_keeps_the_description_and_drops_the_schema() -> None:
    """A ranked match is readable but cannot be run from directly."""
    out = search_dict(search_results().results[0])
    assert out["description"] == "Trending posts across Reddit."
    assert out["platform"] == "reddit"
    assert out["relevance"] == 1.0
    assert "inputSchema" not in out


def test_run_flattens_the_found_branch() -> None:
    """The billed envelope reports found, data, cost, and item count."""
    out = run_dict(run_result())
    assert out["found"] is True
    assert out["data"] == {"posts": [{"title": "hello"}]}
    assert out["costUsd"] == 0.00036
    assert out["items"] == 2
    assert out["resultId"] == "res_123"


def test_provider_is_always_anyapi() -> None:
    """AnyAPI is the customer-facing provider on discovery and on a run."""
    assert detail_dict(catalog_entry())["provider"] == "AnyAPI"
    assert run_dict(run_result())["provider"] == "AnyAPI"


def test_no_output_field_names_a_credit() -> None:
    """Customers never see internal credits, only USD."""
    payloads: list[dict[str, Any]] = [
        summary_dict(catalog_entry()),
        detail_dict(catalog_entry()),
        search_dict(search_results().results[0]),
        run_dict(run_result()),
        error_dict(failing_error()),
    ]
    for payload in payloads:
        assert not [key for key in every_key(payload) if "credit" in key.lower()]


def test_a_price_is_read_through_not_computed() -> None:
    """maxPer1kUsd comes off the wire; nothing multiplies maxUsd by 1,000."""
    pricing = detail_dict(catalog_entry())["pricing"]
    assert pricing["from"]["maxUsd"] == 0.00036
    assert pricing["from"]["maxPer1kUsd"] == 0.3
    assert pricing["from"]["maxPer1kUsd"] != pricing["from"]["maxUsd"] * 1000
    assert pricing["failoverMaxUsd"] == 0.00036
    assert pricing["failoverMaxPer1kUsd"] == 0.3


def test_a_per_call_charge_has_no_per_1k_twin() -> None:
    """A per-call charge is never republished per 1,000 requests."""
    out = run_dict(run_result())
    assert [key for key in out if "per1k" in key.lower()] == []


def test_error_payload_is_readable() -> None:
    """An SDK error becomes something the agent can act on."""
    out = error_dict(failing_error())
    assert out["status"] == 404
    assert out["code"] == "not_found"
    assert out["requestId"] == "req_abc"
    assert "reddit.nope" in out["error"]
