"""Live tests against production. Skipped unless ANYAPI_API_KEY is set.

Only the free tools run here. The one billed proof-of-life call is deliberately
kept out of the suite so it can never be repeated by a re-run.
"""

from __future__ import annotations

import os

import pytest

from llama_index.tools.anyapi import AnyAPIToolSpec

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANYAPI_API_KEY"),
    reason="live tests need ANYAPI_API_KEY",
)


def test_search_is_free_and_ranked() -> None:
    out = AnyAPIToolSpec().search_apis("trending posts on reddit", limit=3)
    assert "error" not in out, out
    assert out["results"], out
    top = out["results"][0]
    assert 0 < top["relevance"] <= 1
    assert "inputSchema" not in top


def test_get_api_publishes_the_schema_and_the_ceiling() -> None:
    out = AnyAPIToolSpec().get_api("reddit.trending_posts")
    assert out["provider"] == "AnyAPI"
    assert out["inputSchema"]["additionalProperties"] is False
    assert out["pricing"]["failoverMaxUsd"] >= out["pricing"]["from"]["maxUsd"]


def test_list_apis_browses_the_catalog() -> None:
    out = AnyAPIToolSpec().list_apis()
    assert out["total"] > 100, out["total"]
    assert "description" not in out["apis"][0]


def test_balance_is_usd() -> None:
    out = AnyAPIToolSpec().get_balance()
    assert isinstance(out["usd"], float)


async def test_the_async_path_talks_to_production() -> None:
    out = await AnyAPIToolSpec().aget_api("reddit.trending_posts")
    assert out["id"] == "reddit.trending_posts"
