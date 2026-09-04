"""The ComponentTool wrappers an Agent consumes: names, descriptions, and parameter schemas."""

from __future__ import annotations

from typing import Any

import pytest
from haystack.tools import ComponentTool

from haystack_integrations.tools.anyapi import ANYAPI_INSTRUCTIONS, anyapi_tools

EXPECTED_NAMES = [
    "anyapi_search_apis",
    "anyapi_list_apis",
    "anyapi_get_api",
    "anyapi_run_api",
    "anyapi_get_balance",
]


def test_five_tools_in_loop_order() -> None:
    """Five tools, not one per SKU, in the order the discovery-then-run loop uses them."""
    tools = anyapi_tools()
    assert [tool.name for tool in tools] == EXPECTED_NAMES
    assert all(isinstance(tool, ComponentTool) for tool in tools)


def test_every_tool_carries_a_non_empty_description() -> None:
    """A tool with no description is invisible to a model."""
    for tool in anyapi_tools():
        assert tool.description
        assert tool.description.strip() == tool.description
        assert len(tool.description) > 50


def test_the_instructions_are_available_for_a_system_prompt() -> None:
    """The AnyAPI system instructions ship with the tools."""
    assert "maxPer1kUsd" in ANYAPI_INSTRUCTIONS
    assert "credit" not in ANYAPI_INSTRUCTIONS.lower()


def test_run_api_parameter_schema_matches_the_sdk_input() -> None:
    """`input` is a free-form JSON object, because a SKU's schema is per-SKU and read at runtime."""
    run_tool = _tool("anyapi_run_api")
    schema = run_tool.parameters

    assert schema["type"] == "object"
    assert sorted(schema["required"]) == ["input", "slug"]
    assert schema["properties"]["slug"]["type"] == "string"
    assert schema["properties"]["input"] == {
        "type": "object",
        "additionalProperties": True,
        "description": schema["properties"]["input"]["description"],
    }
    assert schema["properties"]["input"]["description"]
    assert schema["properties"]["max_items"]["default"] is None
    assert schema["properties"]["summary"]["default"] is False


def test_balance_takes_no_parameters() -> None:
    """The balance tool has a schema with no properties, because the call takes no arguments."""
    schema = _tool("anyapi_get_balance").parameters
    assert schema["properties"] == {}
    assert "required" not in schema


def test_search_parameter_schema_requires_only_a_query() -> None:
    """Search has no browse-everything mode; list does."""
    assert _tool("anyapi_search_apis").parameters["required"] == ["query"]
    assert "required" not in _tool("anyapi_list_apis").parameters


@pytest.mark.parametrize("name", EXPECTED_NAMES)
def test_no_tool_parameter_mentions_credits(name: str) -> None:
    """Customers never see internal credits, on the input side either."""
    schema: dict[str, Any] = _tool(name).parameters
    assert not [key for key in schema.get("properties", {}) if "credit" in key.lower()]


def _tool(name: str) -> ComponentTool:
    return next(tool for tool in anyapi_tools() if tool.name == name)
