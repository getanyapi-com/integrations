"""Smoke the published wheel: import the public surface and build every tool with no key.

The release workflow runs this in a clean venv against the freshly published
version. It must need no network and no API key, and it must exit non-zero on any
failure. Constructing a component or a tool never resolves the key, so an absent
``ANYAPI_API_KEY`` is the expected state here.
"""

from __future__ import annotations

import os
import sys

EXPECTED = [
    "anyapi_search_apis",
    "anyapi_list_apis",
    "anyapi_get_api",
    "anyapi_run_api",
    "anyapi_get_balance",
]


def main() -> int:
    """Run the smoke checks.

    :returns: 0 when the public surface imports and builds, 1 otherwise.
    """
    os.environ.pop("ANYAPI_API_KEY", None)

    from haystack_integrations.components.connectors.anyapi import (
        AnyAPIGetAPI,
        AnyAPIGetBalance,
        AnyAPIListAPIs,
        AnyAPIRunAPI,
        AnyAPISearchAPIs,
    )
    from haystack_integrations.tools.anyapi import ANYAPI_INSTRUCTIONS, anyapi_tools

    for component_class in (
        AnyAPISearchAPIs,
        AnyAPIListAPIs,
        AnyAPIGetAPI,
        AnyAPIRunAPI,
        AnyAPIGetBalance,
    ):
        instance = component_class()
        if "api_key" not in instance.to_dict()["init_parameters"]:
            print(f"FAIL: {component_class.__name__} did not serialize its key reference")
            return 1

    tools = anyapi_tools()
    names = [tool.name for tool in tools]
    if names != EXPECTED:
        print(f"FAIL: tool names {names} do not match {EXPECTED}")
        return 1
    for tool in tools:
        if not tool.description:
            print(f"FAIL: tool {tool.name} has an empty description")
            return 1
        # anyapi_get_balance takes no arguments, so its properties are legitimately empty.
        if "properties" not in tool.parameters:
            print(f"FAIL: tool {tool.name} has no parameter schema")
            return 1

    if not ANYAPI_INSTRUCTIONS:
        print("FAIL: ANYAPI_INSTRUCTIONS is empty")
        return 1

    print(f"anyapi-haystack smoke: ok ({len(tools)} tools, no key required)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
