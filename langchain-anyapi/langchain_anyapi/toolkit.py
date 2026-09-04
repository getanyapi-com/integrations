"""The whole AnyAPI loop as one toolkit."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool, BaseToolkit
from pydantic import Field

from .tools import (
    AnyAPIGetAPI,
    AnyAPIGetBalance,
    AnyAPIListAPIs,
    AnyAPIRunAPI,
    AnyAPISearchAPIs,
)


class AnyAPIToolkit(BaseToolkit):
    """All five AnyAPI tools, sharing one configuration.

    ``get_tools()`` returns search, list, get, run, and balance, which is the
    complete discovery then run loop. Each tool builds its own client on first
    use, so constructing the toolkit needs neither a key nor a socket.
    """

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
        description="Per-request timeout in seconds. Unset means the SDK default.",
    )
    max_retries: int | None = Field(
        default=None,
        description="How many times the SDK retries a retryable failure. "
        "Unset means the SDK default.",
    )

    def _settings(self) -> dict[str, Any]:
        return {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
        }

    def get_tools(self) -> list[BaseTool]:
        """Search, list, get, run, and balance, in that order."""
        settings = self._settings()
        return [
            AnyAPISearchAPIs(**settings),
            AnyAPIListAPIs(**settings),
            AnyAPIGetAPI(**settings),
            AnyAPIRunAPI(**settings),
            AnyAPIGetBalance(**settings),
        ]
