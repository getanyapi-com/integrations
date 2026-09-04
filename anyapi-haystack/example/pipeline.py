"""Run one AnyAPI SKU inside a Haystack pipeline and read the billed envelope.

This is the discovery-then-run loop, wired the way Haystack wires things: the free
``AnyAPIGetAPI`` call reads the strict input schema first, then a pipeline runs the
SKU and hands ``data`` straight to a downstream component.

``reddit.trending_posts`` is billed at a fraction of a cent per request. Run it with
``ANYAPI_API_KEY`` set; get a key at https://getanyapi.com.
"""

from __future__ import annotations

import json

from haystack import Pipeline
from haystack.components.converters import OutputAdapter

from haystack_integrations.components.connectors.anyapi import AnyAPIGetAPI, AnyAPIRunAPI

SLUG = "reddit.trending_posts"


def main() -> None:
    """Read the schema and the price, then run the SKU in a pipeline."""
    described = AnyAPIGetAPI().run(slug=SLUG)
    if described["error"] is not None:
        raise SystemExit(f"could not describe {SLUG}: {described['error']}")
    print("input schema:", json.dumps(described["input_schema"], indent=2))
    print("ceiling for any run, USD:", described["pricing"]["failoverMaxUsd"])

    pipe = Pipeline()
    pipe.add_component("anyapi", AnyAPIRunAPI())
    pipe.add_component("titles", OutputAdapter("{{ data.posts | map(attribute='title') | list }}", list))
    pipe.connect("anyapi.data", "titles.data")

    result = pipe.run({"anyapi": {"slug": SLUG, "input": {"limit": 2}}})
    run = result["anyapi"]
    if run["error"] is not None:
        raise SystemExit(f"run failed: {run['error']}")

    print("provider:", run["provider"])
    print("found:", run["found"], "items:", run["items"], "costUsd:", run["cost_usd"])
    print("titles:", result["titles"]["output"])


if __name__ == "__main__":
    main()
