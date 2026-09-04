"""Unit tests run with no network and no API key, and this enforces both."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from pytest_socket import disable_socket, enable_socket


@pytest.fixture(autouse=True)
def offline_and_keyless(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Block network sockets and remove the key for the duration of a test.

    Unix sockets stay open because asyncio builds its event loop from a
    socketpair.
    """
    monkeypatch.delenv("ANYAPI_API_KEY", raising=False)
    disable_socket(allow_unix_socket=True)
    try:
        yield
    finally:
        enable_socket()
