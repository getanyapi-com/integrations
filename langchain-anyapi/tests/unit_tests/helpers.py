"""Small helpers shared by the unit tests."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

from getanyapi import AnyAPI, AnyAPIError, AsyncAnyAPI

from langchain_anyapi._client import AnyAPIToolBase


def every_key(value: Any) -> Iterator[str]:
    """Yield every mapping key anywhere inside a payload."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from every_key(child)
    elif isinstance(value, list):
        for child in value:
            yield from every_key(child)


def failing_error() -> AnyAPIError:
    """The error the failing stand-in raises, for direct projection tests."""
    return AnyAPIError(
        "sku not found: reddit.nope",
        status=404,
        code="not_found",
        request_id="req_abc",
    )


def with_client(tool: AnyAPIToolBase, client: object) -> AnyAPIToolBase:
    """Install a stand-in as the tool's already-built synchronous client."""
    tool._sync_client = cast(AnyAPI, client)
    return tool


def with_async_client(tool: AnyAPIToolBase, client: object) -> AnyAPIToolBase:
    """Install a stand-in as the tool's already-built asynchronous client."""
    tool._async_client = cast(AsyncAnyAPI, client)
    return tool
