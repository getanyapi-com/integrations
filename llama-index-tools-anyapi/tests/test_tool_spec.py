"""The tool list a model actually sees: names, descriptions, and schemas."""

from __future__ import annotations

import json
from typing import Any

from llama_index.core.tools.tool_spec.base import BaseToolSpec

from llama_index.tools.anyapi import AnyAPIToolSpec
from llama_index.tools.anyapi._descriptions import RUN_API, SEARCH_APIS
from llama_index.tools.anyapi.base import _localize

EXPECTED = ["search_apis", "list_apis", "get_api", "run_api", "get_balance"]


def _descriptions() -> dict[str, str]:
    """Every tool description exactly as a model receives it."""
    return {
        tool.metadata.get_name(): tool.metadata.description
        for tool in AnyAPIToolSpec(api_key="not-used-offline").to_tool_list()
    }


def test_class() -> None:
    names_of_base_classes = [b.__name__ for b in AnyAPIToolSpec.__mro__]
    assert BaseToolSpec.__name__ in names_of_base_classes


def test_spec_functions_are_exactly_the_five_tools() -> None:
    assert [pair[0] for pair in AnyAPIToolSpec.spec_functions] == EXPECTED


def test_constructing_the_spec_needs_no_key_and_no_socket() -> None:
    spec = AnyAPIToolSpec()
    assert spec._clients._sync is None
    assert spec._clients._async is None
    assert len(spec.to_tool_list()) == 5


def test_tool_names() -> None:
    tools = AnyAPIToolSpec(api_key="not-used-offline").to_tool_list()
    assert [tool.metadata.get_name() for tool in tools] == EXPECTED


def test_descriptions_carry_the_anyapi_wording() -> None:
    """The whole package is useless if the shared wording never reaches a model."""
    by_name = _descriptions()
    assert "call get_api for it and use the schema it returns" in by_name["search_apis"]
    assert _localize(SEARCH_APIS) in by_name["search_apis"]
    assert _localize(RUN_API) in by_name["run_api"]
    for name in EXPECTED:
        assert len(by_name[name]) > 100
        # llama-index prepends the rendered signature to the docstring.
        assert by_name[name].startswith(f"{name}(")


def test_descriptions_name_only_tools_that_exist_here() -> None:
    """The shared wording is written for the packages whose tools carry the
    anyapi_ prefix. A LlamaIndex ToolSpec is the namespace, so a description
    that told a model to call anyapi_get_api would name no tool in the list.
    """
    by_name = _descriptions()
    for name in EXPECTED:
        assert "anyapi_" not in by_name[name], name
    assert "get_api" in by_name["search_apis"]
    assert "get_api" in by_name["run_api"]
    assert "run_api" in by_name["list_apis"]
    assert "search_apis" in by_name["list_apis"]
    assert "list_apis" in by_name["search_apis"]
    # The shared constants themselves are untouched, so a template change
    # still propagates by re-copying the file.
    assert "anyapi_get_api" in SEARCH_APIS


def test_localize_only_strips_the_tool_name_prefix() -> None:
    assert _localize("call anyapi_get_api then anyapi_run_api") == (
        "call get_api then run_api"
    )
    assert _localize("AnyAPI is a unified gateway") == "AnyAPI is a unified gateway"


def test_run_api_schema_accepts_sku_id_and_input() -> None:
    tools = {
        tool.metadata.get_name(): tool
        for tool in AnyAPIToolSpec(api_key="not-used-offline").to_tool_list()
    }
    schema: dict[str, Any] = tools["run_api"].metadata.get_parameters_dict()
    assert set(schema["required"]) == {"sku_id", "input"}
    assert schema["properties"]["sku_id"]["type"] == "string"
    assert schema["properties"]["input"]["type"] == "object"
    assert schema["properties"]["summary"]["default"] is False
    assert schema["properties"]["max_items"]["default"] is None
    # Google-style Args lines reach the model as per-parameter descriptions.
    assert "SKU slug" in schema["properties"]["sku_id"]["description"]
    assert "self" not in json.dumps(schema)


def test_search_schema_derived_from_the_signature_does_not_require_a_query() -> None:
    """LlamaIndex derives the parameter schema from the signature, so making
    `query` optional there is what stops the schema demanding it. run_api still
    requires its two, which is what proves the assertion is not vacuous.
    """
    tools = {
        tool.metadata.get_name(): tool
        for tool in AnyAPIToolSpec(api_key="not-used-offline").to_tool_list()
    }
    schema: dict[str, Any] = tools["search_apis"].metadata.get_parameters_dict()
    assert schema.get("required", []) == []
    assert set(schema["properties"]) == {"query", "category", "platform", "limit"}
    assert schema["properties"]["query"]["default"] is None
    run_schema = tools["run_api"].metadata.get_parameters_dict()
    assert set(run_schema["required"]) == {"sku_id", "input"}


def test_each_tool_has_both_a_sync_and_an_async_path() -> None:
    pairs = {
        "search_apis": "asearch_apis",
        "list_apis": "alist_apis",
        "get_api": "aget_api",
        "run_api": "arun_api",
        "get_balance": "aget_balance",
    }
    for tool in AnyAPIToolSpec(api_key="not-used-offline").to_tool_list():
        name = tool.metadata.get_name()
        assert tool.real_fn.__name__ == name
        assert tool.async_fn.__name__ == pairs[name]


def test_get_balance_takes_no_arguments() -> None:
    tools = {
        tool.metadata.get_name(): tool
        for tool in AnyAPIToolSpec(api_key="not-used-offline").to_tool_list()
    }
    assert tools["get_balance"].metadata.get_parameters_dict()["properties"] == {}
