"""Realistic AnyAPI models and stand-in clients, built with no network.

Every fixture here is a real ``getanyapi`` pydantic model, so a change to the
published model shape breaks these tests instead of passing quietly.
"""

from __future__ import annotations

from typing import Any

from getanyapi import (
    AnyAPIError,
    Balance,
    CatalogEntry,
    CatalogSearchResult,
    CatalogSearchResults,
    DiscoveryExecution,
    DiscoveryLane,
    DiscoveryLatency,
    DiscoveryPricing,
    DiscoverySource,
    FlatPricingOffer,
    OutputFound,
    RequestOptions,
    RunResult,
)

# The per-1k figure is deliberately NOT 1000 times the per-request figure, so a
# test can tell a value read off the wire from a value computed locally.
OFFER = FlatPricingOffer(
    model="flat", unit="request", max_usd=0.00036, max_per1k_usd=0.3
)
PRICING = DiscoveryPricing(
    from_offer=OFFER, failover_max_usd=0.00036, failover_max_per1k_usd=0.3
)
EXECUTION = DiscoveryExecution(mode="sync")
SOURCE = DiscoverySource(id="badger", name="Badger", kind="anonymous", artwork_key="bd")


def catalog_entry() -> CatalogEntry:
    """One catalog entry in full, as ``describe`` returns it."""
    return CatalogEntry(
        id="sku_reddit_trending_posts",
        slug="reddit.trending_posts",
        name="Reddit Trending Posts",
        category="social",
        description="Trending posts across Reddit.",
        method="POST",
        path="/v1/apis/reddit.trending_posts/run",
        execution=EXECUTION,
        provider="AnyAPI",
        pricing=PRICING,
        lanes=[DiscoveryLane(pricing=OFFER, source=SOURCE)],
        heavy=False,
        try_eligible=True,
        input_schema={
            "type": "object",
            "properties": {"limit": {"type": "integer"}},
            "additionalProperties": False,
        },
        output_schema={"type": "object"},
        latency=DiscoveryLatency(
            window="30d",
            p50_ms=1200,
            p95_ms=3400,
            p99_ms=8900,
            sample=512,
            basis="service_time_excludes_caller_requested_delay",
        ),
    )


def search_results() -> CatalogSearchResults:
    """One ranked search page, as ``search`` returns it."""
    return CatalogSearchResults(
        results=[
            CatalogSearchResult(
                slug="reddit.trending_posts",
                platform_id="reddit",
                name="Reddit Trending Posts",
                description="Trending posts across Reddit.",
                category="social",
                method="POST",
                path="/v1/apis/reddit.trending_posts/run",
                execution=EXECUTION,
                provider="AnyAPI",
                pricing=PRICING,
                failover=True,
                relevance=1.0,
            )
        ],
        total=1,
        ranking="semantic",
    )


def run_result() -> RunResult[Any]:
    """One billed run envelope, as ``run`` returns it."""
    return RunResult(
        output=OutputFound(found=True, data={"posts": [{"title": "hello"}]}),
        provider="AnyAPI",
        cost_usd=0.00036,
        items=2,
        replayed=False,
        result_id="res_123",
    )


class FakeClient:
    """A stand-in for ``AnyAPI`` that answers from the fixtures above."""

    def __init__(self) -> None:
        """Start with an empty call log."""
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def search(
        self,
        *,
        query: str | None = None,
        category: str | None = None,
        platform: str | None = None,
        limit: int | None = None,
    ) -> CatalogSearchResults:
        """Record the search arguments and answer with the fixture page."""
        self.calls.append(
            (
                "search",
                {
                    "query": query,
                    "category": category,
                    "platform": platform,
                    "limit": limit,
                },
            )
        )
        return search_results()

    def catalog(self, *, category: str | None = None) -> list[CatalogEntry]:
        """Record the browse arguments and answer with one entry."""
        self.calls.append(("catalog", {"category": category}))
        return [catalog_entry()]

    def describe(self, slug: str) -> CatalogEntry:
        """Record the slug and answer with the full entry."""
        self.calls.append(("describe", {"slug": slug}))
        return catalog_entry()

    def run(
        self,
        slug: str,
        input: dict[str, Any],
        *,
        options: RequestOptions | None = None,
    ) -> RunResult[Any]:
        """Record the run arguments and answer with the billed envelope."""
        self.calls.append(("run", {"slug": slug, "input": input, "options": options}))
        return run_result()

    def balance(self) -> Balance:
        """Answer with a wallet balance."""
        self.calls.append(("balance", {}))
        return Balance(usd=4.25)


class FailingClient:
    """A stand-in whose every method raises the SDK's error type."""

    def _boom(self) -> Any:
        raise AnyAPIError(
            "sku not found: reddit.nope",
            status=404,
            code="not_found",
            request_id="req_abc",
        )

    def search(self, **kwargs: Any) -> Any:
        """Raise."""
        return self._boom()

    def catalog(self, **kwargs: Any) -> Any:
        """Raise."""
        return self._boom()

    def describe(self, *args: Any, **kwargs: Any) -> Any:
        """Raise."""
        return self._boom()

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Raise."""
        return self._boom()

    def balance(self) -> Any:
        """Raise."""
        return self._boom()


class AsyncFakeClient:
    """A stand-in for ``AsyncAnyAPI``, awaiting the same fixtures."""

    def __init__(self) -> None:
        """Delegate to a synchronous stand-in and share its call log."""
        self.inner = FakeClient()
        self.calls = self.inner.calls

    async def search(self, **kwargs: Any) -> CatalogSearchResults:
        """Answer with the fixture search page."""
        return self.inner.search(**kwargs)

    async def catalog(self, **kwargs: Any) -> list[CatalogEntry]:
        """Answer with the fixture catalog."""
        return self.inner.catalog(**kwargs)

    async def describe(self, *args: Any, **kwargs: Any) -> CatalogEntry:
        """Answer with the fixture entry."""
        return self.inner.describe(*args, **kwargs)

    async def run(self, *args: Any, **kwargs: Any) -> RunResult[Any]:
        """Answer with the fixture run envelope."""
        return self.inner.run(*args, **kwargs)

    async def balance(self) -> Balance:
        """Answer with the fixture balance."""
        return self.inner.balance()
