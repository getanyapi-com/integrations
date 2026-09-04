"""A component that cannot round-trip cannot live in a saved pipeline. Prove all five can.

Components and tools use different envelopes: a component serializes to
``{"type": ..., "init_parameters": {...}}`` and a tool to ``{"type": ..., "data": {...}}``.
Both are checked here.
"""

from __future__ import annotations

from typing import Any

import pytest
from haystack.utils import Secret

from haystack_integrations.components.connectors.anyapi import (
    AnyAPIGetAPI,
    AnyAPIGetBalance,
    AnyAPIListAPIs,
    AnyAPIRunAPI,
    AnyAPISearchAPIs,
)
from haystack_integrations.tools.anyapi import (
    AnyAPIGetAPITool,
    AnyAPIGetBalanceTool,
    AnyAPIListAPIsTool,
    AnyAPIRunAPITool,
    AnyAPISearchAPIsTool,
)

COMPONENTS = [
    AnyAPISearchAPIs,
    AnyAPIListAPIs,
    AnyAPIGetAPI,
    AnyAPIRunAPI,
    AnyAPIGetBalance,
]

TOOLS = [
    AnyAPISearchAPIsTool,
    AnyAPIListAPIsTool,
    AnyAPIGetAPITool,
    AnyAPIRunAPITool,
    AnyAPIGetBalanceTool,
]


@pytest.mark.parametrize("component_class", COMPONENTS)
def test_component_round_trip(component_class: type[Any]) -> None:
    """to_dict then from_dict returns an identical component dictionary."""
    original = component_class()
    data = original.to_dict()

    assert data["type"].startswith("haystack_integrations.components.connectors.anyapi.")
    assert data["type"].endswith(component_class.__name__)
    assert data["init_parameters"] == {"api_key": {"type": "env_var", "env_vars": ["ANYAPI_API_KEY"], "strict": True}}

    # from_dict follows the Haystack `deserialize_secrets_inplace` convention and
    # mutates what it is given, so it gets its own dictionary here.
    restored = component_class.from_dict(original.to_dict())
    assert isinstance(restored, component_class)
    assert restored.to_dict() == data


@pytest.mark.parametrize("component_class", COMPONENTS)
def test_component_round_trip_keeps_a_custom_env_var(component_class: type[Any]) -> None:
    """A non-default Secret survives the round trip as a reference, never as a value."""
    original = component_class(api_key=Secret.from_env_var("SOME_OTHER_KEY"))
    data = original.to_dict()
    assert data["init_parameters"]["api_key"]["env_vars"] == ["SOME_OTHER_KEY"]
    assert component_class.from_dict(original.to_dict()).to_dict() == data


@pytest.mark.parametrize("tool_class", TOOLS)
def test_tool_round_trip(tool_class: type[Any]) -> None:
    """A tool serializes into the Tool envelope, not the Component one, and round-trips."""
    original = tool_class()
    data = original.to_dict()

    assert data["type"].startswith("haystack_integrations.tools.anyapi.")
    assert data["type"].endswith(tool_class.__name__)
    assert set(data) == {"type", "data"}
    assert data["data"] == {"api_key": {"type": "env_var", "env_vars": ["ANYAPI_API_KEY"], "strict": True}}

    restored = tool_class.from_dict(original.to_dict())
    assert restored.name == original.name
    assert restored.description == original.description
    assert restored.to_dict() == data


@pytest.mark.parametrize("component_class", COMPONENTS)
def test_construction_never_resolves_the_secret(component_class: type[Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """Constructing a component must not read the key, so an import needs no key and no socket."""

    def explode(_self: Secret) -> Any:
        raise AssertionError("Secret.resolve_value was called at construction time")

    monkeypatch.setattr(Secret, "resolve_value", explode)
    instance = component_class()

    assert instance._client is None
    assert instance._async_client is None


@pytest.mark.parametrize("tool_class", TOOLS)
def test_tool_construction_never_resolves_the_secret(tool_class: type[Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """Building a tool must not read the key either; a missing key surfaces only on a call."""

    def explode(_self: Secret) -> Any:
        raise AssertionError("Secret.resolve_value was called at construction time")

    monkeypatch.setattr(Secret, "resolve_value", explode)
    assert tool_class().name.startswith("anyapi_")
