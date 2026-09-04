"""Find an AnyAPI SKU, read its schema, then run it.

Set ANYAPI_API_KEY first. Get a key at https://getanyapi.com. Only the run_api
step charges the USD wallet; search, get and balance are free.
"""

from __future__ import annotations

import json

from llama_index.tools.anyapi import AnyAPIToolSpec


def main() -> None:
    spec = AnyAPIToolSpec()

    found = spec.search_apis("trending posts on reddit", limit=3)
    for match in found["results"]:
        price = match["pricing"]["from"]["maxPer1kUsd"]
        print(f"{match['id']}: {match['name']} (${price}/1k req)")

    # Search results carry no input schema. Read the schema before the run.
    detail = spec.get_api("reddit.trending_posts")
    print(json.dumps(detail["inputSchema"], indent=2))
    print(f"a run of this API costs at most ${detail['pricing']['failoverMaxUsd']}")

    result = spec.run_api("reddit.trending_posts", {"limit": 2})
    print(
        f"found={result['found']} items={result['items']} costUsd={result['costUsd']}"
    )

    # The same five tools, handed to an agent.
    tools = spec.to_tool_list()
    print(f"{len(tools)} tools: {', '.join(t.metadata.get_name() for t in tools)}")


if __name__ == "__main__":
    main()
