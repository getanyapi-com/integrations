# anyapi-haystack

[Haystack](https://haystack.deepset.ai/) components and tools for
[AnyAPI](https://getanyapi.com): one key, hundreds of data and scraping APIs
(Reddit, Instagram, TikTok, YouTube, Google search, web scraping, and more),
billed per request in USD with no subscription.

This package is a thin adapter over the official
[`getanyapi`](https://pypi.org/project/getanyapi/) SDK. HTTP, auth, retries,
pricing, and schema handling belong to that SDK and to the gateway behind it.

## Install

```bash
pip install anyapi-haystack
```

Set your key once. Get one at [getanyapi.com](https://getanyapi.com).

```bash
export ANYAPI_API_KEY="..."
```

## Five components, not 363

AnyAPI has hundreds of SKUs. One component per SKU would blow out any agent's
context window, so this package exposes the same five that the AnyAPI MCP server
does, which together are its proven discovery-then-run loop.

| Component | Tool name | Charges? |
| --- | --- | --- |
| `AnyAPISearchAPIs` | `anyapi_search_apis` | no |
| `AnyAPIListAPIs` | `anyapi_list_apis` | no |
| `AnyAPIGetAPI` | `anyapi_get_api` | no |
| `AnyAPIRunAPI` | `anyapi_run_api` | YES |
| `AnyAPIGetBalance` | `anyapi_get_balance` | no |

The loop: search or list to find a SKU, `AnyAPIGetAPI` to read its strict input
schema, then `AnyAPIRunAPI`. Every input schema is strict, so an unknown field is
rejected rather than ignored, and an input built from a description instead of a
schema usually fails.

## In a pipeline

```python
from haystack import Pipeline
from haystack.components.converters import OutputAdapter
from haystack_integrations.components.connectors.anyapi import AnyAPIRunAPI

pipe = Pipeline()
pipe.add_component("anyapi", AnyAPIRunAPI())
pipe.add_component("titles", OutputAdapter("{{ data.posts | map(attribute='title') | list }}", list))
pipe.connect("anyapi.data", "titles.data")

result = pipe.run({"anyapi": {"slug": "reddit.trending_posts", "input": {"limit": 2}}})
print(result["anyapi"]["cost_usd"], result["titles"]["output"])
```

`AnyAPIRunAPI` publishes its billed envelope as separate sockets so a pipeline can
wire each part where it belongs: `data`, `found`, `cost_usd`, `items`, `provider`,
`result_id`, and `error`. `AnyAPIGetAPI` publishes `api`, plus `input_schema` (the
input to the next step of the loop) and `pricing` (what you read to bound spend).

Every component also implements `run_async` on the SDK's async client, and
`to_dict` / `from_dict`, so a pipeline containing them serializes to YAML with the
key kept as a `Secret` reference rather than a value.

## In an agent

```python
from haystack.components.agents import Agent
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack_integrations.tools.anyapi import ANYAPI_INSTRUCTIONS, anyapi_tools

agent = Agent(
    chat_generator=OpenAIChatGenerator(model="gpt-4o-mini"),
    tools=anyapi_tools(),
    system_prompt=ANYAPI_INSTRUCTIONS,
)
```

`anyapi_tools()` returns the five as `ComponentTool`s carrying the AnyAPI MCP
server's own descriptions. Each is also importable on its own:
`AnyAPISearchAPIsTool`, `AnyAPIListAPIsTool`, `AnyAPIGetAPITool`,
`AnyAPIRunAPITool`, `AnyAPIGetBalanceTool`.

## Money

Prices are USD and are never scaled here. The gateway publishes both `maxUsd`
(what one request is billed) and `maxPer1kUsd` (the same maximum per 1,000
requests); this package reads both off the wire and multiplies nothing. When you
show a catalog price to a person, quote `maxPer1kUsd` and label it `/1k req`. A
per-call charge is reported as `cost_usd` for that one request.

`provider` is always `AnyAPI`. A lane may name a dataset brand or an anonymous
source, and that is the only other source identity you will see.

## Three deliberate departures from the MCP server

- **There is no quote tool.** The MCP server has `quote_api`, but the published
  `getanyapi` SDK exposes no quote method, and adding one would mean hand-rolling
  an authenticated HTTP call beside the SDK. `AnyAPIGetAPI` already publishes
  `pricing.from.maxUsd` (the most a first-choice run is billed) and
  `pricing.failoverMaxUsd` (the ceiling for any run), so spend is still bounded
  before the call.
- **Search results carry no `heavy` marker.** The gateway's ranked search does not
  publish one. `AnyAPIListAPIs` and `AnyAPIGetAPI` do.
- **Search requires a query.** `AnyAPISearchAPIs` has no browse-everything mode;
  use `AnyAPIListAPIs` for that.

## Errors

Every AnyAPI failure is caught at the component boundary and returned on the
`error` socket as `{"error": ..., "status": ..., "code": ..., "requestId": ...}`,
so a failed call gives the agent something recoverable instead of aborting the
run. On that path the unknowable sockets are `None` rather than a fabricated zero.
Anything that is not an AnyAPI error propagates.

## License

MIT. See the `LICENSE` file at the root of this repository.

## Support

[support@getanyapi.com](mailto:support@getanyapi.com)
