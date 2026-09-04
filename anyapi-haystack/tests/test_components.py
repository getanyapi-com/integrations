"""What each component puts on which socket, offline, against realistic fake models."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from getanyapi import AnyAPIError

from haystack_integrations.components.connectors.anyapi import (
    AnyAPIGetAPI,
    AnyAPIGetBalance,
    AnyAPIListAPIs,
    AnyAPIRunAPI,
    AnyAPISearchAPIs,
)

from .fakes import (
    FAILOVER_MAX_PER1K_USD,
    MAX_PER1K_USD,
    MAX_USD,
    FailingAsyncClient,
    FailingClient,
    FakeAsyncClient,
    FakeClient,
    use_client,
)

SOCKETS = {
    AnyAPISearchAPIs: {"results", "total", "ranking", "error"},
    AnyAPIListAPIs: {"apis", "error"},
    AnyAPIGetAPI: {"api", "input_schema", "pricing", "error"},
    AnyAPIRunAPI: {"data", "found", "cost_usd", "items", "provider", "result_id", "error"},
    AnyAPIGetBalance: {"usd", "error"},
}


@pytest.mark.parametrize(("component_class", "expected"), list(SOCKETS.items()))
def test_declared_output_sockets(component_class: type[Any], expected: set[str]) -> None:
    """The declared output sockets are the ones a pipeline can connect to."""
    instance = component_class()
    assert set(instance.__haystack_output__._sockets_dict) == expected


@pytest.mark.parametrize("component_class", list(SOCKETS))
def test_every_component_supports_async(component_class: type[Any]) -> None:
    """Each component ships a run_async on the SDK's async client, not a thread."""
    assert component_class().__haystack_supports_async__ is True


@pytest.mark.parametrize(("component_class", "expected"), list(SOCKETS.items()))
def test_no_output_socket_mentions_credits(component_class: type[Any], expected: set[str]) -> None:
    """Customers never see internal credits. No socket name may contain 'credit'."""
    assert expected == set(component_class().__haystack_output__._sockets_dict)
    assert not [name for name in expected if "credit" in name.lower()]


def test_search_maps_the_ranked_page() -> None:
    """Search puts the projected matches, the published total, and the ranking mode on sockets."""
    component = AnyAPISearchAPIs()
    client = FakeClient()
    use_client(component, client)

    out = component.run(query="reddit", category="social", platform="reddit", limit=5)

    assert out["error"] is None
    assert out["ranking"] == "semantic"
    # total is the gateway's count of relevant matches before the limit, not len(results).
    assert out["total"] == 7
    assert len(out["results"]) == 1
    match = out["results"][0]
    assert match["id"] == "reddit.trending_posts"
    assert match["platform"] == "reddit"
    assert match["description"] == "Trending posts across Reddit."
    assert match["relevance"] == 1.0
    assert "inputSchema" not in match
    assert client.calls == [("search", {"query": "reddit", "category": "social", "platform": "reddit", "limit": 5})]


def test_search_async_matches_the_sync_path() -> None:
    """run_async goes through AsyncAnyAPI and lands the same values on the same sockets."""
    component = AnyAPISearchAPIs()
    use_client(component, FakeAsyncClient())

    out = asyncio.run(component.run_async(query="reddit"))

    assert out["total"] == 7
    assert out["results"][0]["id"] == "reddit.trending_posts"


def test_list_maps_browse_summaries() -> None:
    """Browse emits summaries with no description and no schemas."""
    component = AnyAPIListAPIs()
    client = FakeClient()
    use_client(component, client)

    out = component.run(category="social")

    assert out["error"] is None
    summary = out["apis"][0]
    assert summary["id"] == "reddit.trending_posts"
    assert summary["execution"] == "sync"
    assert summary["heavy"] is False
    assert "description" not in summary
    assert "inputSchema" not in summary
    assert client.calls == [("catalog", {"category": "social"})]


def test_list_async_matches_the_sync_path() -> None:
    """The async browse lands the same summaries."""
    component = AnyAPIListAPIs()
    use_client(component, FakeAsyncClient())
    assert asyncio.run(component.run_async())["apis"][0]["id"] == "reddit.trending_posts"


def test_get_api_lifts_the_schema_and_the_price_out_of_the_detail() -> None:
    """The two sockets the loop needs next are the same objects already inside `api`."""
    component = AnyAPIGetAPI()
    use_client(component, FakeClient())

    out = component.run(slug="reddit.trending_posts")

    assert out["error"] is None
    assert out["api"]["provider"] == "AnyAPI"
    assert out["input_schema"] is out["api"]["inputSchema"]
    assert out["pricing"] is out["api"]["pricing"]
    assert out["input_schema"]["additionalProperties"] is False
    assert out["api"]["lanes"] == [{"pricing": out["pricing"]["from"], "source": "Badger"}]
    assert out["api"]["latency"]["p99Ms"] == 4300


def test_get_api_async_matches_the_sync_path() -> None:
    """The async describe lands the same definition."""
    component = AnyAPIGetAPI()
    use_client(component, FakeAsyncClient())
    assert asyncio.run(component.run_async(slug="reddit.trending_posts"))["api"]["id"] == "reddit.trending_posts"


def test_run_splits_the_billed_envelope() -> None:
    """The run envelope arrives as separate sockets, each value read off the wire."""
    component = AnyAPIRunAPI()
    client = FakeClient()
    use_client(component, client)

    out = component.run(slug="reddit.trending_posts", input={"limit": 2}, max_items=2)

    assert out["error"] is None
    assert out["found"] is True
    assert out["data"] == {"posts": [{"title": "a post", "author": "someone"}], "nextCursor": None}
    assert out["provider"] == "AnyAPI"
    assert out["cost_usd"] == MAX_USD
    assert out["items"] == 2
    assert out["result_id"] == "res_01HZZ"
    assert client.calls == [
        ("run", {"slug": "reddit.trending_posts", "input": {"limit": 2}, "options": {"max_items": 2}})
    ]


def test_run_passes_no_options_when_none_were_asked_for() -> None:
    """Response shaping is opt-in, so an unshaped call sends no options at all."""
    component = AnyAPIRunAPI()
    client = FakeClient()
    use_client(component, client)

    component.run(slug="reddit.trending_posts", input={"limit": 2})

    assert client.calls[0][1]["options"] is None


def test_run_async_matches_the_sync_path() -> None:
    """The async run lands the same billed envelope."""
    component = AnyAPIRunAPI()
    use_client(component, FakeAsyncClient())

    out = asyncio.run(component.run_async(slug="reddit.trending_posts", input={"limit": 2}))

    assert out["cost_usd"] == MAX_USD
    assert out["provider"] == "AnyAPI"


def test_balance_reads_usd() -> None:
    """The wallet balance is USD, and it is the only fact the gateway publishes here."""
    component = AnyAPIGetBalance()
    use_client(component, FakeClient())
    assert component.run() == {"usd": 4.21, "error": None}


def test_balance_async_matches_the_sync_path() -> None:
    """The async balance read lands the same value."""
    component = AnyAPIGetBalance()
    use_client(component, FakeAsyncClient())
    assert asyncio.run(component.run_async())["usd"] == 4.21


def test_prices_are_read_through_never_computed() -> None:
    """maxPer1kUsd comes off the wire. The fakes make it NOT 1000x maxUsd, so a multiply fails here."""
    assert MAX_PER1K_USD != MAX_USD * 1000

    component = AnyAPIGetAPI()
    use_client(component, FakeClient())
    pricing = component.run(slug="reddit.trending_posts")["pricing"]

    assert pricing["from"]["maxUsd"] == MAX_USD
    assert pricing["from"]["maxPer1kUsd"] == MAX_PER1K_USD
    assert pricing["failoverMaxPer1kUsd"] == FAILOVER_MAX_PER1K_USD


def test_no_projected_field_name_mentions_credits() -> None:
    """Nothing anywhere in a projected payload may name internal credits."""
    describe = AnyAPIGetAPI()
    use_client(describe, FakeClient())
    search = AnyAPISearchAPIs()
    use_client(search, FakeClient())
    run = AnyAPIRunAPI()
    use_client(run, FakeClient())

    payloads = [
        describe.run(slug="reddit.trending_posts"),
        search.run(query="reddit"),
        run.run(slug="reddit.trending_posts", input={}),
    ]
    for name in _field_names(payloads):
        assert "credit" not in name.lower(), name


def _field_names(value: Any) -> list[str]:
    if isinstance(value, dict):
        names: list[str] = []
        for key, nested in value.items():
            names.append(str(key))
            names.extend(_field_names(nested))
        return names
    if isinstance(value, list):
        return [name for item in value for name in _field_names(item)]
    return []


ERROR = AnyAPIError("upstream refused the request", status=502, request_id="req_01HZZ", code="upstream_error")


@pytest.mark.parametrize(
    ("component_class", "kwargs", "unknowable"),
    [
        (AnyAPISearchAPIs, {"query": "reddit"}, {"results": [], "total": 0, "ranking": None}),
        (AnyAPIListAPIs, {}, {"apis": []}),
        (AnyAPIGetAPI, {"slug": "x.y"}, {"api": None, "input_schema": None, "pricing": None}),
        (
            AnyAPIRunAPI,
            {"slug": "x.y", "input": {}},
            {
                "data": None,
                "found": None,
                "cost_usd": None,
                "items": None,
                "provider": "AnyAPI",
                "result_id": None,
            },
        ),
        (AnyAPIGetBalance, {}, {"usd": None}),
    ],
)
def test_an_anyapi_error_becomes_a_payload_not_a_raise(
    component_class: type[Any], kwargs: dict[str, Any], unknowable: dict[str, Any]
) -> None:
    """A failed call gives the agent something recoverable instead of aborting the run."""
    component = component_class()
    use_client(component, FailingClient(ERROR))

    out = component.run(**kwargs)

    assert out["error"] == {
        "error": "upstream refused the request",
        "status": 502,
        "code": "upstream_error",
        "requestId": "req_01HZZ",
    }
    for socket, value in unknowable.items():
        assert out[socket] == value


@pytest.mark.parametrize(
    ("component_class", "kwargs"),
    [
        (AnyAPISearchAPIs, {"query": "reddit"}),
        (AnyAPIListAPIs, {}),
        (AnyAPIGetAPI, {"slug": "x.y"}),
        (AnyAPIRunAPI, {"slug": "x.y", "input": {}}),
        (AnyAPIGetBalance, {}),
    ],
)
def test_an_anyapi_error_becomes_a_payload_on_the_async_path_too(
    component_class: type[Any], kwargs: dict[str, Any]
) -> None:
    """The async path catches the same errors at the same boundary."""
    component = component_class()
    use_client(component, FailingAsyncClient(ERROR))
    assert asyncio.run(component.run_async(**kwargs))["error"]["status"] == 502


def test_a_non_anyapi_error_propagates() -> None:
    """Only AnyAPI failures are converted. Everything else is a real bug and must surface."""
    component = AnyAPIRunAPI()
    use_client(component, FailingClient(ValueError("boom")))

    with pytest.raises(ValueError, match="boom"):
        component.run(slug="x.y", input={})


def test_provider_is_always_anyapi() -> None:
    """AnyAPI is the top-level provider on every path, including the failure path."""
    ok = AnyAPIRunAPI()
    use_client(ok, FakeClient())
    failed = AnyAPIRunAPI()
    use_client(failed, FailingClient(ERROR))

    assert ok.run(slug="x.y", input={})["provider"] == "AnyAPI"
    assert failed.run(slug="x.y", input={})["provider"] == "AnyAPI"
