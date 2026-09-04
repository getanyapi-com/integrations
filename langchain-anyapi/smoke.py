"""Smoke the published wheel: import it, build the tools, check the surface.

The release workflow runs this against the freshly published version in a
clean venv. It needs no API key and no network: constructing a tool is lazy,
so nothing here opens a socket.
"""

from __future__ import annotations

import sys

from langchain_anyapi import (
    ANYAPI_INSTRUCTIONS,
    AnyAPIToolkit,
    __version__,
)

EXPECTED = [
    "anyapi_search_apis",
    "anyapi_list_apis",
    "anyapi_get_api",
    "anyapi_run_api",
    "anyapi_get_balance",
]


def main() -> int:
    """Return 0 when the public surface is intact, 1 otherwise."""
    problems: list[str] = []

    tools = AnyAPIToolkit().get_tools()
    names = [tool.name for tool in tools]
    if names != EXPECTED:
        problems.append(f"tool names are {names}, expected {EXPECTED}")

    for tool in tools:
        if not tool.description.strip():
            problems.append(f"{tool.name} has an empty description")
        if tool.args_schema is None:
            problems.append(f"{tool.name} has no args_schema")

    if not ANYAPI_INSTRUCTIONS.strip():
        problems.append("ANYAPI_INSTRUCTIONS is empty")

    for problem in problems:
        print(f"FAIL: {problem}", file=sys.stderr)
    if problems:
        return 1

    print(f"langchain-anyapi {__version__} smoke ok: {', '.join(names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
