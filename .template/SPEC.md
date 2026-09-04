# Shared spec for the three AnyAPI agent-framework packages

## What is being built

Three independently published Python packages that let an agent framework call
AnyAPI. Each one is a thin adapter over the ALREADY PUBLISHED official SDK
`getanyapi` (PyPI, currently 0.35.3). Nothing here reimplements HTTP, auth,
retries, pricing, schema handling, or the customer-safety scan: those belong to
`getanyapi` and to the gateway behind it.

| PyPI name | Directory | Import root |
|---|---|---|
| `langchain-anyapi` | `langchain-anyapi/` | `langchain_anyapi` |
| `llama-index-tools-anyapi` | `llama-index-tools-anyapi/` | `llama_index.tools.anyapi` |
| `anyapi-haystack` | `anyapi-haystack/` | `haystack_integrations.components.anyapi` |

## The tool set: five tools, not 363

AnyAPI has 363 SKUs. Emitting one tool per SKU would blow out any agent's
context window. Instead every package exposes the SAME five tools, which are the
AnyAPI MCP server's proven discovery-then-run loop:

| Tool | Charges? | What it does |
|---|---|---|
| `anyapi_search_apis` | no | ranked search over the catalog, descriptions kept, schemas omitted |
| `anyapi_list_apis` | no | browse summaries, optionally filtered by category |
| `anyapi_get_api` | no | one API in full: strict input schema, output schema, per-lane USD pricing, 30-day latency |
| `anyapi_run_api` | YES | execute one SKU with a normalized input payload |
| `anyapi_get_balance` | no | remaining wallet balance in USD |

The loop the descriptions teach: search or list to find a SKU, `get_api` to read
its strict input schema, then `run_api`. An input built from a description
rather than a schema usually fails, and the descriptions say so.

There is deliberately NO quote tool. The MCP server has `quote_api`, but the
published `getanyapi` SDK exposes no quote method, and adding one would mean
hand-rolling an authenticated HTTP call to `POST /v1/apis/{id}/quote` beside the
SDK. `anyapi_get_api` already publishes `pricing.from.maxUsd` (the most a
first-choice run is billed) and `pricing.failoverMaxUsd` (the ceiling for any
run), so an agent can still bound its spend before calling. Record this in the
package README.

## Money and copy invariants, non-negotiable

- USD only. Customers never see internal credits. Never emit a field whose name
  contains "credit".
- Never scale a price. `maxUsd` (one request) and `maxPer1kUsd` (the same
  maximum per 1,000 requests) are BOTH published by the gateway; read them, do
  not multiply. A per-call charge (`costUsd`) never gains a per-1k twin.
- `provider` is always the literal `"AnyAPI"`. Never expose a routing provider
  slug. A lane's `source` name (a dataset brand or an anonymous animal like
  "Badger") is safe and is the only source identity that may appear.
- Canonical hosts only: `https://getanyapi.com` and `https://api.getanyapi.com`.
  Support is `support@getanyapi.com`. NEVER `anyapi.dev` and never an `app.`
  subdomain.
- No em dash and no en dash glyphs in any file. Use ASCII `-` or rephrase.
  `scripts/check-dashes.sh` at the repo root enforces this.

## Shared code you are given

`.template/_projection.py` and `.template/_descriptions.py` in the repo root are
finished and verified against live production discovery. Copy BOTH into your
package (as a private module, name it to suit the package) and use them
unchanged apart from the module docstring. Do not re-derive the projections.

Each package ships its own copy on purpose. A fourth shared distribution just to
hold ~110 lines would be an extra release to coordinate on every change, and
each package must install standalone.

## SDK surface you may use

```python
from getanyapi import AnyAPI, AsyncAnyAPI, AnyAPIError
c = AnyAPI(api_key=...)          # falls back to env ANYAPI_API_KEY
c.catalog(category=None)          -> list[CatalogEntry]
c.search(query=..., category=None, platform=None, limit=None) -> CatalogSearchResults
c.describe(slug)                  -> CatalogEntry   # carries inputSchema/outputSchema/latency
c.run(slug, input, options=RequestOptions)          -> RunResult[Any]
c.balance()                       -> Balance        # .usd
```

`RequestOptions` is a TypedDict supporting `fields: list[str]`, `max_items: int`,
`summary: bool` (response shaping, never changes the charge), plus `timeout`,
`max_retries`, `idempotency_key`.

`AsyncAnyAPI` mirrors all of the above with `await`. Use it for the async path;
do not run the sync client in a thread.

Errors: every failure raises a subclass of `AnyAPIError`, which carries
`.status`, `.code`, and `.request_id`. Catch `AnyAPIError` at the tool boundary
and return `error_dict(exc)` from the projection module, so the agent gets a
readable, recoverable payload instead of an aborted run. This mirrors what the
MCP server does with `toolError`. Let anything that is not an `AnyAPIError`
propagate.

## Client lifecycle

Construct the `AnyAPI` / `AsyncAnyAPI` client lazily on first use and reuse it,
so importing the package never requires a key and constructing a tool never
opens a socket. A missing key must surface only when a tool is actually called.

## Gate for every package

```
ruff check . && ruff format --check . && mypy && pytest
```

`mypy` runs in strict mode against the package source, configured in
`pyproject.toml`. Tests live in `tests/` and must pass with NO network access
and NO API key present, except for a clearly separated live test that is skipped
unless `ANYAPI_API_KEY` is set.

Keep every source file at or under 300 code lines, excluding blank lines and
comments.

## Packaging

Build backend `hatchling`. `requires-python = ">=3.10"`. License MIT (the repo
root `LICENSE` is the one copy; reference it, do not duplicate the text).
Author `AnyAPI <support@getanyapi.com>`. Version `0.1.0`.

Every package depends on `getanyapi>=0.35,<1` plus its own framework core.

`[project.urls]`: Homepage `https://getanyapi.com`, Documentation
`https://getanyapi.com/docs`, Issues on the package repository.

Each package directory also needs a `smoke.py` at its root: a script the release
workflow runs against the freshly published wheel in a clean venv. It must
import the public surface, construct the tools WITHOUT a key, assert the tool
names and that a description is non-empty, and exit non-zero on failure. It must
not need network or a key.
