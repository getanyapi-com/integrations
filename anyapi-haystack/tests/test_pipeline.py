"""The components inside a real Pipeline: wiring, socket consumption, and YAML round trip.

This is the shape the live proof used. A socket that feeds a downstream component is
consumed by that connection and drops out of the pipeline result; the sockets that
were not connected, including the billed cost, still come back.
"""

from __future__ import annotations

from typing import Any

from haystack import Pipeline
from haystack.components.converters import OutputAdapter

from haystack_integrations.components.connectors.anyapi import AnyAPIRunAPI, AnyAPISearchAPIs

from .fakes import MAX_USD, FakeClient, use_client


def _pipeline() -> Pipeline:
    pipe = Pipeline()
    pipe.add_component("anyapi", AnyAPIRunAPI())
    # The same template the README and example/pipeline.py show, on the same data shape.
    pipe.add_component("titles", OutputAdapter("{{ data.posts | map(attribute='title') | list }}", list))
    pipe.connect("anyapi.data", "titles.data")
    return pipe


def test_run_component_feeds_a_downstream_component() -> None:
    """`data` connects to another component's input socket, which is the whole point of a socket."""
    pipe = _pipeline()
    use_client(pipe.get_component("anyapi"), FakeClient())

    result = pipe.run({"anyapi": {"slug": "reddit.trending_posts", "input": {"limit": 2}}})

    assert result["titles"]["output"] == ["a post"]
    # `data` was consumed by the connection; the unconnected sockets still come back,
    # so a caller can still read what the run cost.
    assert "data" not in result["anyapi"]
    assert result["anyapi"]["cost_usd"] == MAX_USD
    assert result["anyapi"]["provider"] == "AnyAPI"
    assert result["anyapi"]["items"] == 2


def test_a_pipeline_containing_the_components_round_trips_through_yaml() -> None:
    """A pipeline that cannot be saved and reloaded cannot be shipped as configuration."""
    pipe = Pipeline()
    pipe.add_component("search", AnyAPISearchAPIs())
    pipe.add_component("anyapi", AnyAPIRunAPI())

    restored = Pipeline.loads(pipe.dumps())
    payload: dict[str, Any] = restored.to_dict()

    assert set(payload["components"]) == {"search", "anyapi"}
    for name in ("search", "anyapi"):
        assert payload["components"][name]["init_parameters"]["api_key"] == {
            "type": "env_var",
            "env_vars": ["ANYAPI_API_KEY"],
            "strict": True,
        }
