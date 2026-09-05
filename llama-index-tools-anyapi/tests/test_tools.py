"""The tool boundary: options, error payloads, and the real async path."""

from __future__ import annotations

from typing import Any

import pytest
from getanyapi import (
    AnyAPIError,
    Balance,
    CatalogEntry,
    CatalogSearchResults,
    InsufficientBalanceError,
    RunResult,
)

from llama_index.tools.anyapi import AnyAPIToolSpec
from llama_index.tools.anyapi.base import _options


class StubClient:
    """Stands in for AnyAPI and AsyncAnyAPI; every method records its call."""

    def __init__(self, result: Any = None, raises: Exception | None = None) -> None:
        self.result = result
        self.raises = raises
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def _answer(self, name: str, **kwargs: Any) -> Any:
        self.calls.append((name, kwargs))
        if self.raises is not None:
            raise self.raises
        return self.result

    def search(self, **kwargs: Any) -> Any:
        return self._answer("search", **kwargs)

    def catalog(self, **kwargs: Any) -> Any:
        return self._answer("catalog", **kwargs)

    def describe(self, slug: str) -> Any:
        return self._answer("describe", slug=slug)

    def run(self, slug: str, payload: dict[str, Any], **kwargs: Any) -> Any:
        return self._answer("run", slug=slug, input=payload, **kwargs)

    def balance(self) -> Any:
        return self._answer("balance")


class AsyncStubClient(StubClient):
    """The same recorder, awaited."""

    async def search(self, **kwargs: Any) -> Any:
        return self._answer("search", **kwargs)

    async def catalog(self, **kwargs: Any) -> Any:
        return self._answer("catalog", **kwargs)

    async def describe(self, slug: str) -> Any:
        return self._answer("describe", slug=slug)

    async def run(self, slug: str, payload: dict[str, Any], **kwargs: Any) -> Any:
        return self._answer("run", slug=slug, input=payload, **kwargs)

    async def balance(self) -> Any:
        return self._answer("balance")


def wire(spec: AnyAPIToolSpec, client: StubClient) -> StubClient:
    """Install one stub as both clients of an already-constructed spec."""
    spec._clients._sync = client  # type: ignore[assignment]
    spec._clients._async = client  # type: ignore[assignment]
    return client


def test_options_are_omitted_entirely_when_nothing_is_shaped() -> None:
    assert _options(None, None, False) is None
    assert _options(["title"], 5, True) == {
        "fields": ["title"],
        "max_items": 5,
        "summary": True,
    }


def test_run_api_passes_shaping_options_through() -> None:
    spec = AnyAPIToolSpec(api_key="offline")
    client = wire(spec, StubClient(result=_found_run()))
    spec.run_api("reddit.trending_posts", {"limit": 2}, max_items=1)
    assert client.calls[0][1]["options"] == {"max_items": 1}


def test_search_returns_the_ranked_envelope(
    search_results: CatalogSearchResults,
) -> None:
    spec = AnyAPIToolSpec(api_key="offline")
    wire(spec, StubClient(result=search_results))
    out = spec.search_apis("reddit trending", limit=5)
    assert out["total"] == 1
    assert out["ranking"] == "semantic"
    assert out["results"][0]["id"] == "reddit.trending_posts"


def test_search_by_category_alone_reaches_the_sdk_with_no_query(
    search_results: CatalogSearchResults,
) -> None:
    """`category` with no query enumerates that category."""
    spec = AnyAPIToolSpec(api_key="offline")
    client = wire(spec, StubClient(result=search_results))
    out = spec.search_apis(category="social")
    assert client.calls == [
        (
            "search",
            {"query": None, "category": "social", "platform": None, "limit": None},
        )
    ]
    assert out["results"][0]["id"] == "reddit.trending_posts"


def test_search_by_platform_alone_reaches_the_sdk_with_no_query(
    search_results: CatalogSearchResults,
) -> None:
    """`platform` with no query enumerates that platform."""
    spec = AnyAPIToolSpec(api_key="offline")
    client = wire(spec, StubClient(result=search_results))
    out = spec.search_apis(platform="reddit")
    assert client.calls == [
        (
            "search",
            {"query": None, "category": None, "platform": "reddit", "limit": None},
        )
    ]
    assert out["total"] == 1


async def test_async_search_by_platform_alone_reaches_the_sdk_too(
    search_results: CatalogSearchResults,
) -> None:
    """The async path carries the same optional query."""
    spec = AnyAPIToolSpec(api_key="offline")
    client = wire(spec, AsyncStubClient(result=search_results))
    await spec.asearch_apis(platform="reddit")
    assert client.calls == [
        (
            "search",
            {"query": None, "category": None, "platform": "reddit", "limit": None},
        )
    ]


def test_a_search_with_no_scope_at_all_is_the_sdk_error_payload() -> None:
    """The "at least one" rule is enforced by the SDK below this package, and
    its client-side AnyAPIError comes back as this package's error payload.
    """
    spec = AnyAPIToolSpec(api_key="offline")
    assert spec.search_apis() == {
        "error": "search needs at least one of query, category, or platform",
        "status": 0,
    }


def test_list_apis_returns_summaries(entry: CatalogEntry) -> None:
    spec = AnyAPIToolSpec(api_key="offline")
    wire(spec, StubClient(result=[entry]))
    out = spec.list_apis(category="social")
    assert out["total"] == 1
    assert out["apis"][0]["name"] == "Reddit Trending Posts"


def test_get_balance_is_usd(entry: CatalogEntry) -> None:
    spec = AnyAPIToolSpec(api_key="offline")
    wire(spec, StubClient(result=Balance(usd=0.0499)))
    assert spec.get_balance() == {"usd": 0.0499}


@pytest.mark.parametrize(
    "method",
    ["search_apis", "list_apis", "get_api", "run_api", "get_balance"],
)
def test_every_tool_converts_an_anyapi_error_into_a_payload(method: str) -> None:
    spec = AnyAPIToolSpec(api_key="offline")
    wire(spec, StubClient(raises=InsufficientBalanceError("broke", status=402)))
    args: dict[str, list[Any]] = {
        "search_apis": ["cats"],
        "list_apis": [],
        "get_api": ["reddit.trending_posts"],
        "run_api": ["reddit.trending_posts", {}],
        "get_balance": [],
    }
    out = getattr(spec, method)(*args[method])
    assert out == {"error": "broke", "status": 402}


def test_a_non_anyapi_error_still_propagates() -> None:
    spec = AnyAPIToolSpec(api_key="offline")
    wire(spec, StubClient(raises=RuntimeError("bug")))
    with pytest.raises(RuntimeError):
        spec.get_balance()


def test_a_missing_key_surfaces_only_when_a_tool_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANYAPI_API_KEY", raising=False)
    spec = AnyAPIToolSpec()
    tools = spec.to_tool_list()
    out = spec.get_balance()
    assert len(tools) == 5
    assert out["status"] == 401 or "API key" in out["error"]


async def test_the_async_path_uses_the_async_client(
    entry: CatalogEntry,
) -> None:
    spec = AnyAPIToolSpec(api_key="offline")
    client = wire(spec, AsyncStubClient(result=entry))
    out = await spec.aget_api("reddit.trending_posts")
    assert out["id"] == "reddit.trending_posts"
    assert client.calls == [("describe", {"slug": "reddit.trending_posts"})]


async def test_acall_on_the_tool_reaches_the_awaitable_method(
    entry: CatalogEntry,
) -> None:
    spec = AnyAPIToolSpec(api_key="offline")
    wire(spec, AsyncStubClient(result=entry))
    tool = next(t for t in spec.to_tool_list() if t.metadata.get_name() == "get_api")
    output = await tool.acall(sku_id="reddit.trending_posts")
    assert output.raw_output["id"] == "reddit.trending_posts"


async def test_async_error_becomes_a_payload_too() -> None:
    spec = AnyAPIToolSpec(api_key="offline")
    wire(spec, AsyncStubClient(raises=AnyAPIError("nope", status=500)))
    assert await spec.arun_api("x", {}) == {"error": "nope", "status": 500}


def _found_run() -> RunResult[Any]:
    return RunResult[Any].model_validate(
        {
            "output": {"found": True, "data": {}},
            "provider": "AnyAPI",
            "costUsd": 0.0,
            "items": 0,
            "replayed": False,
        }
    )
