"""Lazy construction of the two ``getanyapi`` clients.

Importing this package must not require an API key and building the tool spec
must not open a socket, so neither client is constructed until a tool actually
runs. ``getanyapi`` falls back to the ``ANYAPI_API_KEY`` environment variable
when ``api_key`` is ``None``, and raises ``AnyAPIError`` when neither is set,
which is why that construction happens inside the tool's error boundary.
"""

from __future__ import annotations

from getanyapi import AnyAPI, AsyncAnyAPI


class LazyClients:
    """One sync and one async AnyAPI client, each built once on first use."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key
        self._sync: AnyAPI | None = None
        self._async: AsyncAnyAPI | None = None

    def sync_client(self) -> AnyAPI:
        """The shared blocking client, constructed on first call."""
        if self._sync is None:
            self._sync = AnyAPI(api_key=self._api_key)
        return self._sync

    def async_client(self) -> AsyncAnyAPI:
        """The shared awaitable client, constructed on first call."""
        if self._async is None:
            self._async = AsyncAnyAPI(api_key=self._api_key)
        return self._async
