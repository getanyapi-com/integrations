"""The five tools, exercised with stand-in clients and no network."""

from __future__ import annotations

import json
from typing import Any

import pytest
from langchain_core.messages import ToolCall, ToolMessage
from langchain_core.tools import BaseTool

from langchain_anyapi import (
    AnyAPIGetAPI,
    AnyAPIGetBalance,
    AnyAPIListAPIs,
    AnyAPIRunAPI,
    AnyAPISearchAPIs,
    AnyAPIToolkit,
)
from langchain_anyapi import _descriptions as d
from langchain_anyapi._client import AnyAPIToolBase

from .fakes import AsyncFakeClient, FailingClient, FakeClient
from .helpers import with_async_client, with_client

NAMES = [
    "anyapi_search_apis",
    "anyapi_list_apis",
    "anyapi_get_api",
    "anyapi_run_api",
    "anyapi_get_balance",
]

EXAMPLE_ARGS: dict[str, dict[str, Any]] = {
    "anyapi_search_apis": {"query": "reddit trending posts"},
    "anyapi_list_apis": {"category": "social"},
    "anyapi_get_api": {"sku_id": "reddit.trending_posts"},
    "anyapi_run_api": {"sku_id": "reddit.trending_posts", "input": {"limit": 2}},
    "anyapi_get_balance": {},
}


def tools() -> list[AnyAPIToolBase]:
    """One instance of each tool, built without a key."""
    return [
        AnyAPISearchAPIs(),
        AnyAPIListAPIs(),
        AnyAPIGetAPI(),
        AnyAPIRunAPI(),
        AnyAPIGetBalance(),
    ]


def test_toolkit_returns_the_five_tools_in_the_loop_order() -> None:
    """One line wires search, list, get, run, and balance."""
    kit_tools = AnyAPIToolkit().get_tools()
    assert [tool.name for tool in kit_tools] == NAMES
    assert all(isinstance(tool, BaseTool) for tool in kit_tools)


def test_descriptions_are_the_shared_ones_and_are_not_empty() -> None:
    """The wording is the MCP server's, so it cannot drift silently."""
    expected = {
        "anyapi_search_apis": d.SEARCH_APIS,
        "anyapi_list_apis": d.LIST_APIS,
        "anyapi_get_api": d.GET_API,
        "anyapi_run_api": d.RUN_API,
        "anyapi_get_balance": d.GET_BALANCE,
    }
    for tool in tools():
        assert tool.description == expected[tool.name]
        assert tool.description.strip()


def test_every_tool_declares_an_args_schema_for_its_documented_shape() -> None:
    """The example call for each tool validates against its own schema."""
    for tool in tools():
        schema = tool.get_input_schema()
        assert schema(**EXAMPLE_ARGS[tool.name])


def test_construction_needs_no_key_and_opens_no_client() -> None:
    """Importing and constructing must not need a key or a socket."""
    for tool in tools():
        assert tool._sync_client is None
        assert tool._async_client is None


def test_a_missing_key_surfaces_as_an_error_payload_on_first_call() -> None:
    """The key is only ever needed when a tool is actually called."""
    out = AnyAPIGetBalance().invoke({})
    assert "API key" in out["error"]


def test_search_passes_its_arguments_and_projects_the_page() -> None:
    """A ranked page keeps total and ranking beside the matches."""
    client = FakeClient()
    tool = with_client(AnyAPISearchAPIs(), client)
    out = tool.invoke(
        {"query": "reddit", "category": "social", "platform": "reddit", "limit": 5}
    )
    assert client.calls[0] == (
        "search",
        {"query": "reddit", "category": "social", "platform": "reddit", "limit": 5},
    )
    assert out["total"] == 1
    assert out["ranking"] == "semantic"
    assert out["results"][0]["id"] == "reddit.trending_posts"


def test_list_browses_a_category() -> None:
    """Browsing returns summaries only."""
    client = FakeClient()
    out = with_client(AnyAPIListAPIs(), client).invoke({"category": "social"})
    assert client.calls[0] == ("catalog", {"category": "social"})
    assert out["apis"][0]["id"] == "reddit.trending_posts"
    assert "description" not in out["apis"][0]


def test_get_returns_the_full_definition() -> None:
    """get_api is what an agent reads before its first run."""
    client = FakeClient()
    tool = with_client(AnyAPIGetAPI(), client)
    out = tool.invoke({"sku_id": "reddit.trending_posts"})
    assert client.calls[0] == ("describe", {"slug": "reddit.trending_posts"})
    assert out["inputSchema"]["properties"] == {"limit": {"type": "integer"}}


def test_run_reports_the_actual_charge() -> None:
    """The billed envelope says what this call cost, in USD."""
    client = FakeClient()
    out = with_client(AnyAPIRunAPI(), client).invoke(
        {"sku_id": "reddit.trending_posts", "input": {"limit": 2}}
    )
    assert client.calls[0] == (
        "run",
        {"slug": "reddit.trending_posts", "input": {"limit": 2}, "options": None},
    )
    assert out["costUsd"] == 0.00036
    assert out["found"] is True


def test_run_forwards_only_the_shaping_options_that_were_given() -> None:
    """Shaping trims the response and never changes the charge."""
    client = FakeClient()
    with_client(AnyAPIRunAPI(), client).invoke(
        {
            "sku_id": "reddit.trending_posts",
            "input": {"limit": 2},
            "fields": ["title"],
            "max_items": 1,
        }
    )
    assert client.calls[0][1]["options"] == {"fields": ["title"], "max_items": 1}


def test_balance_is_usd() -> None:
    """The wallet is quoted in USD, never in anything else."""
    out = with_client(AnyAPIGetBalance(), FakeClient()).invoke({})
    assert out == {"usd": 4.25}


def test_every_tool_answers_an_sdk_error_with_a_payload() -> None:
    """A failed call is recoverable, not an aborted run."""
    for tool in tools():
        out = with_client(tool, FailingClient()).invoke(EXAMPLE_ARGS[tool.name])
        assert out["status"] == 404
        assert out["code"] == "not_found"
        assert out["requestId"] == "req_abc"


def test_a_tool_call_yields_json_content_the_model_can_read() -> None:
    """response_format is "content"; LangChain serializes the dict to JSON."""
    tool = with_client(AnyAPIGetBalance(), FakeClient())
    call = ToolCall(name=tool.name, args={}, id="1", type="tool_call")
    message = tool.invoke(call)
    assert isinstance(message, ToolMessage)
    assert json.loads(str(message.content)) == {"usd": 4.25}
    assert message.artifact is None


def test_every_tool_implements_its_own_async_path() -> None:
    """The async path uses AsyncAnyAPI, not the sync client in a thread."""
    for tool in tools():
        assert type(tool)._arun is not BaseTool._arun


@pytest.mark.asyncio
async def test_async_invoke_projects_the_same_payloads() -> None:
    """The async path answers with the same shapes as invoke."""
    for tool in tools():
        client = AsyncFakeClient()
        out = await with_async_client(tool, client).ainvoke(EXAMPLE_ARGS[tool.name])
        assert client.calls
        assert "error" not in out
