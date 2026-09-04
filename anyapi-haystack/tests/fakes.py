"""Realistic fake AnyAPI models and clients, built from the real ``getanyapi`` types.

The models here are constructed through the published pydantic classes rather than
as loose dictionaries, so a field rename or a type change in ``getanyapi`` breaks
these tests instead of silently changing what the components emit.

The pricing figures are deliberately NOT in a 1,000x relationship. ``max_usd`` is
0.00036 and ``max_per1k_usd`` is 0.29, so any test that reads 0.29 back has proved
the value came off the wire and was not computed from the per-request price.
"""

from __future__ import annotations

from typing import Any

from getanyapi import (
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

MAX_USD = 0.00036
MAX_PER1K_USD = 0.29
FAILOVER_MAX_USD = 0.00036
FAILOVER_MAX_PER1K_USD = 0.31


def offer() -> FlatPricingOffer:
    """A flat per-request offer whose two denominations are not a multiple of each other."""
    return FlatPricingOffer(model="flat", unit="request", maxUsd=MAX_USD, maxPer1kUsd=MAX_PER1K_USD)


def pricing() -> DiscoveryPricing:
    """The cheapest offer plus the failover ceiling."""
    # `from` is the wire name of the cheapest offer and a Python keyword, so this one
    # model is validated from a wire-shaped dictionary rather than a keyword call.
    return DiscoveryPricing.model_validate(
        {
            "from": offer(),
            "failoverMaxUsd": FAILOVER_MAX_USD,
            "failoverMaxPer1kUsd": FAILOVER_MAX_PER1K_USD,
        }
    )


def entry() -> CatalogEntry:
    """One full catalog entry, as ``describe`` returns it."""
    return CatalogEntry(
        id="sku_reddit_trending_posts",
        slug="reddit.trending_posts",
        name="Reddit trending posts",
        category="social",
        description="Trending posts across Reddit.",
        method="POST",
        path="/v1/run/reddit.trending_posts",
        execution=DiscoveryExecution(mode="sync"),
        provider="AnyAPI",
        pricing=pricing(),
        lanes=[
            DiscoveryLane(
                pricing=offer(),
                source=DiscoverySource(id="src_badger", name="Badger", kind="anonymous", artworkKey="badger"),
            )
        ],
        heavy=False,
        tryEligible=True,
        tryMaxItems=5,
        failover=True,
        excludesCallerDelay=True,
        inputSchema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"limit": {"type": "integer"}},
        },
        outputSchema={"type": "object", "properties": {"title": {"type": "string"}}},
        latency=DiscoveryLatency(
            window="30d",
            p50Ms=820,
            p95Ms=2100,
            p99Ms=4300,
            sample=1462,
            basis="service_time_excludes_caller_requested_delay",
        ),
    )


def search_result() -> CatalogSearchResult:
    """One ranked search match."""
    return CatalogSearchResult(
        slug="reddit.trending_posts",
        platformId="reddit",
        name="Reddit trending posts",
        category="social",
        description="Trending posts across Reddit.",
        method="POST",
        path="/v1/run/reddit.trending_posts",
        execution=DiscoveryExecution(mode="sync"),
        provider="AnyAPI",
        pricing=pricing(),
        tryMaxItems=5,
        failover=True,
        excludesCallerDelay=True,
        relevance=1.0,
    )


def search_results() -> CatalogSearchResults:
    """A ranked search page whose ``total`` is larger than the list it carries."""
    return CatalogSearchResults(results=[search_result()], total=7, ranking="semantic")


def run_result() -> RunResult[Any]:
    """A successful billed run envelope."""
    return RunResult[Any](
        output=OutputFound[Any](
            found=True,
            data={"posts": [{"title": "a post", "author": "someone"}], "nextCursor": None},
        ),
        provider="AnyAPI",
        costUsd=MAX_USD,
        items=2,
        replayed=False,
        resultId="res_01HZZ",
    )


def balance() -> Balance:
    """A wallet balance."""
    return Balance(usd=4.21)


class FakeClient:
    """Stands in for ``AnyAPI``: records every call and returns the fake models.

    ``FakeAsyncClient`` subclasses this to stand in for ``AsyncAnyAPI``, so the two
    paths return the same values and only the awaiting differs.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def search(
        self,
        *,
        query: str,
        category: str | None = None,
        platform: str | None = None,
        limit: int | None = None,
    ) -> CatalogSearchResults:
        """Record the search and return the fake page."""
        self.calls.append(("search", {"query": query, "category": category, "platform": platform, "limit": limit}))
        return search_results()

    def catalog(self, *, category: str | None = None) -> list[CatalogEntry]:
        """Record the browse and return one fake entry."""
        self.calls.append(("catalog", {"category": category}))
        return [entry()]

    def describe(self, slug: str) -> CatalogEntry:
        """Record the describe and return the fake entry."""
        self.calls.append(("describe", {"slug": slug}))
        return entry()

    def run(self, slug: str, input: dict[str, Any], *, options: RequestOptions | None = None) -> RunResult[Any]:
        """Record the run and return the fake billed envelope."""
        self.calls.append(("run", {"slug": slug, "input": input, "options": options}))
        return run_result()

    def balance(self) -> Balance:
        """Record the balance read and return the fake balance."""
        self.calls.append(("balance", {}))
        return balance()


class FakeAsyncClient(FakeClient):
    """The same recorder, with every method awaitable, standing in for ``AsyncAnyAPI``."""

    async def search(  # type: ignore[override]
        self,
        *,
        query: str,
        category: str | None = None,
        platform: str | None = None,
        limit: int | None = None,
    ) -> CatalogSearchResults:
        """Await-able search."""
        return super().search(query=query, category=category, platform=platform, limit=limit)

    async def catalog(self, *, category: str | None = None) -> list[CatalogEntry]:  # type: ignore[override]
        """Await-able browse."""
        return super().catalog(category=category)

    async def describe(self, slug: str) -> CatalogEntry:  # type: ignore[override]
        """Await-able describe."""
        return super().describe(slug)

    async def run(  # type: ignore[override]
        self, slug: str, input: dict[str, Any], *, options: RequestOptions | None = None
    ) -> RunResult[Any]:
        """Await-able run."""
        return super().run(slug, input, options=options)

    async def balance(self) -> Balance:  # type: ignore[override]
        """Await-able balance read."""
        return super().balance()


class FailingClient:
    """Raises one ``AnyAPIError`` from every method, to exercise the error socket."""

    def __init__(self, exc: BaseException) -> None:
        self.exc = exc

    def __getattr__(self, _name: str) -> Any:
        def raise_it(*_args: Any, **_kwargs: Any) -> Any:
            raise self.exc

        return raise_it


class FailingAsyncClient(FailingClient):
    """The same, with awaitable methods."""

    def __getattr__(self, _name: str) -> Any:
        async def raise_it(*_args: Any, **_kwargs: Any) -> Any:
            raise self.exc

        return raise_it


def use_client(component: Any, client: Any) -> None:
    """Install a stand-in as both the sync and the async client, bypassing the lazy build.

    :param component: The AnyAPI component to install into.
    :param client: The stand-in client.
    """
    component._client = client
    component._async_client = client
