"""LangChain's standard tool tests against the live AnyAPI gateway.

Only the four free tools are here. `anyapi_run_api` is deliberately left out:
the standard suite invokes a tool several times, and every run of an API
charges the USD wallet.

The whole module is skipped unless `ANYAPI_API_KEY` is set.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from langchain_core.tools import BaseTool
from langchain_tests.integration_tests import ToolsIntegrationTests
from typing_extensions import override

from langchain_anyapi import (
    AnyAPIGetAPI,
    AnyAPIGetBalance,
    AnyAPIListAPIs,
    AnyAPISearchAPIs,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANYAPI_API_KEY"),
    reason="live AnyAPI gateway tests need ANYAPI_API_KEY",
)


class TestSearchAPIsIntegration(ToolsIntegrationTests):
    """Live standard tests for anyapi_search_apis. Free to call."""

    @override
    @property
    def tool_constructor(self) -> type[BaseTool]:
        return AnyAPISearchAPIs

    @override
    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"query": "reddit trending posts", "limit": 3}


class TestListAPIsIntegration(ToolsIntegrationTests):
    """Live standard tests for anyapi_list_apis. Free to call."""

    @override
    @property
    def tool_constructor(self) -> type[BaseTool]:
        return AnyAPIListAPIs

    @override
    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"category": "social"}


class TestGetAPIIntegration(ToolsIntegrationTests):
    """Live standard tests for anyapi_get_api. Free to call."""

    @override
    @property
    def tool_constructor(self) -> type[BaseTool]:
        return AnyAPIGetAPI

    @override
    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"sku_id": "reddit.trending_posts"}


class TestGetBalanceIntegration(ToolsIntegrationTests):
    """Live standard tests for anyapi_get_balance. Free to call."""

    @override
    @property
    def tool_constructor(self) -> type[BaseTool]:
        return AnyAPIGetBalance
