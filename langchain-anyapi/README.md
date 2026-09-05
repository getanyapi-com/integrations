# langchain-anyapi

LangChain tools for [AnyAPI](https://getanyapi.com): hundreds of data and
scraping APIs (Reddit, Instagram, TikTok, YouTube, Google search, web scraping,
and more) behind one key, billed per request in USD, no subscriptions.

```bash
pip install langchain-anyapi
```

Set `ANYAPI_API_KEY`, or pass `api_key=` to a tool or the toolkit. A key with
starter credit is free at <https://getanyapi.com>.

## The whole loop in one line

```python
from langchain.agents import create_agent
from langchain_anyapi import ANYAPI_INSTRUCTIONS, AnyAPIToolkit

agent = create_agent(
    "anthropic:claude-sonnet-4-5",
    tools=AnyAPIToolkit().get_tools(),
    system_prompt=ANYAPI_INSTRUCTIONS,
)
```

Or take one tool at a time:

```python
from langchain_anyapi import AnyAPIGetAPI, AnyAPIRunAPI, AnyAPISearchAPIs

AnyAPISearchAPIs().invoke({"query": "reddit trending posts"})
AnyAPIGetAPI().invoke({"sku_id": "reddit.trending_posts"})
AnyAPIRunAPI().invoke({"sku_id": "reddit.trending_posts", "input": {"limit": 2}})
```

## Five tools, not one per API

| Tool | Charges? | What it does |
|---|---|---|
| `anyapi_search_apis` | no | ranked search over the catalog, descriptions kept, schemas omitted |
| `anyapi_list_apis` | no | browse summaries, optionally filtered by category |
| `anyapi_get_api` | no | one API in full: strict input schema, output schema, per-lane USD pricing, 30-day latency |
| `anyapi_run_api` | YES | execute one API with a normalized input payload |
| `anyapi_get_balance` | no | remaining wallet balance in USD |

AnyAPI publishes hundreds of APIs. One tool per API would not fit an agent's
context, so these five teach the loop instead: search or list to find an API,
`anyapi_get_api` to read its strict input schema, then `anyapi_run_api`. Input
schemas reject unknown fields rather than ignoring them, so an input built from
a description instead of a schema usually fails.

## Money

Prices are USD and come off the wire exactly as the gateway published them.
Every static price is quoted in both denominations: `maxUsd` is what one
request is billed, and `maxPer1kUsd` is the same price per 1,000 requests.
Nothing in this package multiplies one into the other. A run reports its actual
charge as `costUsd`.

There is no quote tool here. The AnyAPI MCP server has one, but the published
`getanyapi` SDK exposes no quote method, and adding one would mean hand-rolling
an authenticated HTTP call beside the SDK. `anyapi_get_api` already publishes
`pricing.from.maxUsd`, the most a first-choice run is billed, and
`pricing.failoverMaxUsd`, the ceiling for any run, so an agent can bound its
spend before it calls. One further difference from the MCP server's tools:
search results carry no `heavy` marker.

## Behavior worth knowing

- Both `_run` and `_arun` are real. The async path uses `AsyncAnyAPI`, not the
  sync client on a thread.
- The client is built on first use. Importing this package and constructing a
  tool need neither a key nor a socket, so a missing key surfaces only when a
  tool is actually called.
- A failed call returns a readable payload with `error`, `status`, and where
  the gateway sent them `code` and `requestId`, rather than aborting the run.
- `response_format` is `"content"`. LangChain serializes the returned dict to
  JSON for the tool message either way, so an artifact would only carry a
  second copy of the same payload.
- `anyapi_run_api` takes `fields`, `max_items`, and `summary` to trim a large
  response. None of them change what you are charged.

## Development

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy && pytest
```

Unit tests run with sockets blocked and no key. The integration tests call the
live gateway and are skipped unless `ANYAPI_API_KEY` is set; they cover the free
tools only, because the standard suite invokes a tool repeatedly and every run
of an API charges the wallet.

## Links

- Homepage: <https://getanyapi.com>
- Docs: <https://getanyapi.com/docs>
- Support: support@getanyapi.com

MIT licensed.
