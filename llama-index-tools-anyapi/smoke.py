"""Smoke the freshly published wheel: no network, no API key, no repo.

The release workflow copies this file next to a clean venv that has installed
the exact published version, so it may only touch the public surface.
"""

from __future__ import annotations

import sys

EXPECTED = ["search_apis", "list_apis", "get_api", "run_api", "get_balance"]


def main() -> int:
    from llama_index.tools.anyapi import AnyAPIToolSpec

    tools = AnyAPIToolSpec().to_tool_list()
    names = [tool.metadata.get_name() for tool in tools]
    if names != EXPECTED:
        print(f"smoke: expected tools {EXPECTED}, got {names}")
        return 1
    for tool in tools:
        if not tool.metadata.description.strip():
            print(f"smoke: tool {tool.metadata.get_name()} has an empty description")
            return 1
    search = next(t for t in tools if t.metadata.get_name() == "search_apis")
    if "call get_api for it" not in search.metadata.description:
        print("smoke: the AnyAPI wording did not reach the tool description")
        return 1
    print(f"smoke: ok, {len(tools)} tools: {', '.join(names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
