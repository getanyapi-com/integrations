# LlamaIndex Tools Integration: AnyAPI

[AnyAPI](https://getanyapi.com) is one key and one USD wallet in front of
hundreds of data and scraping APIs: Reddit, Instagram, TikTok, YouTube,
LinkedIn, Google search and maps, Amazon, and clean JSON from pages that block
bots. There is no subscription; you are billed per request in USD.

This package exposes AnyAPI to LlamaIndex as a single `AnyAPIToolSpec`.

## Install

```bash
pip install llama-index-tools-anyapi
```

Set `ANYAPI_API_KEY`, or pass `api_key=` to the tool spec. Get a key at
[getanyapi.com](https://getanyapi.com).

## Usage

```python
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI
from llama_index.tools.anyapi import AnyAPIToolSpec

agent = FunctionAgent(
    tools=AnyAPIToolSpec().to_tool_list(),
    llm=OpenAI(model="gpt-4.1"),
)

print(await agent.run("What is trending on Reddit right now?"))
```

The tools also work on their own:

```python
spec = AnyAPIToolSpec()
spec.search_apis("trending posts on reddit", limit=3)
spec.get_api("reddit.trending_posts")  # read the strict input schema
spec.run_api("reddit.trending_posts", {"limit": 2})
```

Every tool has an awaitable twin (`asearch_apis`, `aget_api`, `arun_api`, and
so on) backed by `AsyncAnyAPI`, so `await tool.acall(...)` talks to AnyAPI
asynchronously rather than running the blocking client on a thread.

A runnable script is in [`examples/basic_usage.py`](examples/basic_usage.py).

## The five tools

AnyAPI publishes hundreds of SKUs. One tool per SKU would exhaust any agent's
context, so this spec ships the AnyAPI MCP server's discovery-then-run loop
instead.

| Tool | Charges? | What it does |
|---|---|---|
| `search_apis` | no | ranked search over the catalog, descriptions kept, schemas omitted |
| `list_apis` | no | browse summaries, optionally filtered by category |
| `get_api` | no | one API in full: strict input schema, output schema, per-lane USD pricing, 30-day latency |
| `run_api` | YES | execute one SKU with a normalized input payload |
| `get_balance` | no | remaining wallet balance in USD |

Search and browse results carry no input schema. Call `get_api` for an API
before your first `run_api` on it and build the input from the schema it
returns: every input schema is strict, so an invented field name fails the call.

## Prices

Every static price is published in both denominations and neither is derived
from the other. `maxUsd` is what one request is billed; `maxPer1kUsd` is the
same price per 1,000 requests. Quote the per-1k figure to a person, and never
multiply a price yourself. A per-call charge comes back as `costUsd` on the run
result.

There is no quote tool. `get_api` already publishes `pricing.from.maxUsd`, the
most a first-choice run is billed, and `pricing.failoverMaxUsd`, the ceiling for
any run of that API, so an agent can bound its spend before calling.

## Departures from the AnyAPI MCP server

The tool descriptions are the MCP server's own wording, because it already
encodes what agents get wrong. Three things differ here:

- there is no quote tool, for the reason above;
- search results carry no `heavy` marker;
- the MCP server names its tools `anyapi_search_apis`, `anyapi_get_api` and so
  on, and the shared wording is written that way. Here the tool spec is the
  namespace, so the tools are `search_apis`, `list_apis`, `get_api`, `run_api`
  and `get_balance`, and the `anyapi_` prefix is stripped from the descriptions
  when they are bound, so every tool a description names is one you can call.

## License

MIT. See the `LICENSE` file at the root of the repository.
