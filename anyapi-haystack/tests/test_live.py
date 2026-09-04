"""Live tests against production AnyAPI, skipped unless ANYAPI_API_KEY is set.

FREE components only. Nothing here runs a SKU, so nothing here spends the wallet.
Run them with ``pytest -m integration``.
"""

from __future__ import annotations

import os

import pytest

from haystack_integrations.components.connectors.anyapi import (
    AnyAPIGetAPI,
    AnyAPIGetBalance,
    AnyAPIListAPIs,
    AnyAPISearchAPIs,
)

# Captured at import, before the suite-wide fixture removes it from the environment.
LIVE_KEY = os.environ.get("ANYAPI_API_KEY")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not LIVE_KEY, reason="ANYAPI_API_KEY is not set"),
]

SLUG = "reddit.trending_posts"


@pytest.fixture(autouse=True)
def _keep_the_live_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Put the real key back, since these tests need it."""
    assert LIVE_KEY is not None
    monkeypatch.setenv("ANYAPI_API_KEY", LIVE_KEY)


def test_live_search_returns_ranked_matches() -> None:
    """Search is free and returns descriptions with a relevance score."""
    out = AnyAPISearchAPIs().run(query="reddit trending posts", limit=5)

    assert out["error"] is None
    assert out["results"]
    assert out["ranking"] in {"semantic", "keyword"}
    assert 0 < out["results"][0]["relevance"] <= 1


def test_live_list_returns_summaries() -> None:
    """Browse is free and returns summaries with USD pricing in both denominations."""
    out = AnyAPIListAPIs().run()

    assert out["error"] is None
    assert out["apis"]
    offer = out["apis"][0]["pricing"]["from"]
    assert offer["maxUsd"] >= 0
    assert offer["maxPer1kUsd"] >= 0


def test_live_get_api_publishes_the_schema_and_the_ceiling() -> None:
    """Describe is free and gives the strict input schema plus the spend ceiling."""
    out = AnyAPIGetAPI().run(slug=SLUG)

    assert out["error"] is None
    assert out["api"]["provider"] == "AnyAPI"
    assert out["input_schema"]
    assert out["pricing"]["failoverMaxUsd"] >= out["pricing"]["from"]["maxUsd"]


def test_live_balance_is_usd() -> None:
    """Balance is free and reports USD."""
    out = AnyAPIGetBalance().run()

    assert out["error"] is None
    assert isinstance(out["usd"], float)
