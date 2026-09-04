"""LangChain's own standard tool tests, run against all five tools.

`init_from_env_params` stays empty on purpose: the key is read by the
`getanyapi` client from `ANYAPI_API_KEY` when a tool is called, so a tool built
from the environment has no attribute to assert at construction time.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from langchain_tests.unit_tests import ToolsUnitTests
from typing_extensions import override

from langchain_anyapi import (
    AnyAPIGetAPI,
    AnyAPIGetBalance,
    AnyAPIListAPIs,
    AnyAPIRunAPI,
    AnyAPISearchAPIs,
)


class TestSearchAPIsUnit(ToolsUnitTests):
    """Standard unit tests for anyapi_search_apis."""

    @override
    @property
    def tool_constructor(self) -> type[BaseTool]:
        return AnyAPISearchAPIs

    @override
    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"query": "reddit trending posts"}


class TestListAPIsUnit(ToolsUnitTests):
    """Standard unit tests for anyapi_list_apis."""

    @override
    @property
    def tool_constructor(self) -> type[BaseTool]:
        return AnyAPIListAPIs

    @override
    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"category": "social"}


class TestGetAPIUnit(ToolsUnitTests):
    """Standard unit tests for anyapi_get_api."""

    @override
    @property
    def tool_constructor(self) -> type[BaseTool]:
        return AnyAPIGetAPI

    @override
    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"sku_id": "reddit.trending_posts"}


class TestRunAPIUnit(ToolsUnitTests):
    """Standard unit tests for anyapi_run_api. Nothing here calls it."""

    @override
    @property
    def tool_constructor(self) -> type[BaseTool]:
        return AnyAPIRunAPI

    @override
    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"sku_id": "reddit.trending_posts", "input": {"limit": 2}}


class TestGetBalanceUnit(ToolsUnitTests):
    """Standard unit tests for anyapi_get_balance."""

    @override
    @property
    def tool_constructor(self) -> type[BaseTool]:
        return AnyAPIGetBalance
