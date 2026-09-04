"""Fixtures that build realistic gateway payloads out of the real SDK models.

Every fixture is validated through the published ``getanyapi`` pydantic models
rather than hand-built dictionaries, so a model change in a future SDK release
breaks these tests instead of silently changing what the tools emit.
"""

from __future__ import annotations

from typing import Any

import pytest
from getanyapi import CatalogEntry, CatalogSearchResults, RunResult

_PRICING: dict[str, Any] = {
    "from": {
        "model": "flat",
        "unit": "request",
        "maxUsd": 0.00036,
        "maxPer1kUsd": 0.36,
    },
    "failoverMaxUsd": 0.00036,
    "failoverMaxPer1kUsd": 0.36,
}

_ENTRY: dict[str, Any] = {
    "id": "reddit.trending_posts",
    "slug": "reddit.trending_posts",
    "name": "Reddit Trending Posts",
    "category": "social",
    "description": "Trending posts across Reddit.",
    "method": "POST",
    "path": "/v1/apis/reddit.trending_posts/run",
    "execution": {"mode": "sync"},
    "provider": "AnyAPI",
    "pricing": _PRICING,
    "lanes": [
        {
            "pricing": {
                "model": "flat",
                "unit": "request",
                "maxUsd": 0.00036,
                "maxPer1kUsd": 0.36,
            },
            "source": {
                "id": "badger",
                "name": "Badger",
                "kind": "anonymous",
                "artworkKey": "badger",
            },
        }
    ],
    "heavy": False,
    "tryEligible": True,
    "inputSchema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {"limit": {"type": "integer"}},
    },
    "outputSchema": {"type": "object"},
    "latency": {
        "window": "30d",
        "p50Ms": 812,
        "p95Ms": 2100,
        "p99Ms": 4300,
        "sample": 1204,
        "basis": "service_time_excludes_caller_requested_delay",
    },
}


@pytest.fixture
def entry() -> CatalogEntry:
    """One catalog entry as the discovery endpoint publishes it."""
    return CatalogEntry.model_validate(_ENTRY)


@pytest.fixture
def search_results() -> CatalogSearchResults:
    """One page of ranked search matches."""
    return CatalogSearchResults.model_validate(
        {
            "results": [
                {
                    "slug": "reddit.trending_posts",
                    "platformId": "reddit",
                    "name": "Reddit Trending Posts",
                    "description": "Trending posts across Reddit.",
                    "category": "social",
                    "method": "POST",
                    "path": "/v1/apis/reddit.trending_posts/run",
                    "execution": {"mode": "sync"},
                    "provider": "AnyAPI",
                    "pricing": _PRICING,
                    "failover": True,
                    "relevance": 1.0,
                }
            ],
            "total": 1,
            "ranking": "semantic",
        }
    )


@pytest.fixture
def run_result() -> RunResult[Any]:
    """One billed run envelope carrying a found payload."""
    return RunResult[Any].model_validate(
        {
            "output": {"found": True, "data": {"posts": [{"title": "hello"}]}},
            "provider": "AnyAPI",
            "costUsd": 0.00036,
            "items": 2,
            "replayed": False,
            "resultId": "req_abc123",
        }
    )
