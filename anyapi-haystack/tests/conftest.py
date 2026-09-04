"""Test fixtures: every test runs with no AnyAPI key in the environment."""

from __future__ import annotations

from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Remove ``ANYAPI_API_KEY`` so nothing in the offline suite can reach the network."""
    monkeypatch.delenv("ANYAPI_API_KEY", raising=False)
    yield
