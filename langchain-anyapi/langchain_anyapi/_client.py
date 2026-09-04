"""Shared configuration and lazy ``getanyapi`` client ownership.

Importing this package never needs a key and constructing a tool never opens a
socket: the client is built on first use and reused afterwards. A missing key
therefore surfaces from the first call, as an error payload the agent can read,
rather than as an exception at construction time.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal

from getanyapi import AnyAPI, AnyAPIError, AsyncAnyAPI, RequestOptions
from langchain_core.tools import BaseTool
from pydantic import Field, PrivateAttr

from ._projection import error_dict


class AnyAPIToolBase(BaseTool):
    """Configuration every AnyAPI tool shares, plus its two lazy clients."""

    api_key: str | None = Field(
        default=None,
        description="AnyAPI key. Falls back to the ANYAPI_API_KEY environment "
        "variable when unset.",
    )
    base_url: str | None = Field(
        default=None,
        description="Override the AnyAPI gateway base URL. Unset means the "
        "SDK default, https://api.getanyapi.com.",
    )
    timeout: float | None = Field(
        default=None,
        description="Per-request timeout in seconds. Unset means the SDK "
        "default. Read an API's latency p95/p99 before lowering it.",
    )
    max_retries: int | None = Field(
        default=None,
        description="How many times the SDK retries a retryable failure. "
        "Unset means the SDK default.",
    )

    # LangChain serializes a dict return to JSON for the ToolMessage content
    # under BOTH response formats (verified on langchain-core 1.6.1), so the
    # model reads the same structured JSON either way. "content" is kept
    # because an artifact would carry a second copy of that same dict and
    # would make a plain .invoke(args) return a (dict, dict) tuple instead of
    # the dict itself.
    response_format: Literal["content", "content_and_artifact"] = "content"

    _sync_client: AnyAPI | None = PrivateAttr(default=None)
    _async_client: AsyncAnyAPI | None = PrivateAttr(default=None)

    def _client_kwargs(self) -> dict[str, Any]:
        """Only the settings the caller actually chose, so SDK defaults win."""
        kwargs: dict[str, Any] = {"api_key": self.api_key}
        if self.base_url is not None:
            kwargs["base_url"] = self.base_url
        if self.timeout is not None:
            kwargs["timeout"] = self.timeout
        if self.max_retries is not None:
            kwargs["max_retries"] = self.max_retries
        return kwargs

    def client(self) -> AnyAPI:
        """The shared synchronous client, built on first use."""
        if self._sync_client is None:
            self._sync_client = AnyAPI(**self._client_kwargs())
        return self._sync_client

    def async_client(self) -> AsyncAnyAPI:
        """The shared asynchronous client, built on first use."""
        if self._async_client is None:
            self._async_client = AsyncAnyAPI(**self._client_kwargs())
        return self._async_client

    def call(self, fn: Callable[[AnyAPI], dict[str, Any]]) -> dict[str, Any]:
        """Run one synchronous SDK call, answering failures with a payload."""
        try:
            return fn(self.client())
        except AnyAPIError as exc:
            return error_dict(exc)

    async def acall(
        self, fn: Callable[[AsyncAnyAPI], Awaitable[dict[str, Any]]]
    ) -> dict[str, Any]:
        """Run one asynchronous SDK call, answering failures with a payload."""
        try:
            return await fn(self.async_client())
        except AnyAPIError as exc:
            return error_dict(exc)


def run_options(
    fields: list[str] | None, max_items: int | None, summary: bool | None
) -> RequestOptions | None:
    """Build response-shaping options, or None when the caller asked for none.

    These trim the response the agent has to read. They never change what the
    call is charged.
    """
    options: RequestOptions = {}
    if fields is not None:
        options["fields"] = fields
    if max_items is not None:
        options["max_items"] = max_items
    if summary is not None:
        options["summary"] = summary
    return options or None
