# AnyAPI agent-framework integrations

Three independently published Python packages that let an agent framework call
[AnyAPI](https://getanyapi.com): any API, one wallet, USD, no subscriptions.

| PyPI name | Framework | Import root |
|---|---|---|
| `langchain-anyapi` | LangChain | `langchain_anyapi` |
| `llama-index-tools-anyapi` | LlamaIndex | `llama_index.tools.anyapi` |
| `anyapi-haystack` | Haystack | `haystack_integrations` |

## They are adapters, not clients

Each package is a thin adapter over the official AnyAPI Python SDK
[`getanyapi`](https://pypi.org/project/getanyapi/), whose source lives in
[`getanyapi-com/sdks`](https://github.com/getanyapi-com/sdks). None of them
implements HTTP, authentication, retries, idempotency, pricing, schema
handling, or the customer-safety scan. All of that belongs to `getanyapi` and
to the gateway behind it, and duplicating any of it would create a second
source of truth for prices.

## Five tools, not 363

AnyAPI publishes 363 APIs. Emitting one tool per API would exhaust any agent's
context window before it asked its first question. Every package instead
exposes the same five tools, which are the AnyAPI MCP server's proven
discovery-then-run loop:

```
                  +-------------------+
   "I need        |  search_apis      |  ranked, descriptions kept,
    TikTok        |  list_apis        |  schemas omitted
    comments"     +---------+---------+
                            |
                            v
                  +-------------------+
                  |  get_api          |  the strict input schema,
                  |                   |  USD pricing, 30-day latency
                  +---------+---------+
                            |
                            v
                  +-------------------+
                  |  run_api          |  the only tool that spends
                  +-------------------+

   get_balance    free, any time
```

The step agents skip is the middle one. Search and browse results carry no
input schema on purpose, so an agent that builds a call from a description
rather than a schema will usually fail: every AnyAPI input schema is strict and
rejects unknown fields rather than ignoring them. The tool descriptions in
`_descriptions.py` say so in the AnyAPI MCP server's own wording, because that
wording was written against real agent failures.

## There is no quote tool

The MCP server has a `quote_api` tool that prices a call before running it. The
published `getanyapi` SDK exposes no quote method, and adding one here would
mean hand-rolling an authenticated HTTP call to `POST /v1/apis/{id}/quote`
beside the SDK, which is exactly the duplication these packages exist to avoid.

`get_api` already publishes what a call can cost: `pricing.from.maxUsd` is the
most a first-choice run is billed, and `pricing.failoverMaxUsd` is the most any
run of that API can be billed. An agent can bound its spend from those two
numbers. Restoring a real quote tool is a `getanyapi` change, not a
per-framework one.

## Money and naming rules these packages must not break

- USD only. Internal credits never appear in any output.
- Prices are never scaled. `maxUsd` (one request) and `maxPer1kUsd` (the same
  maximum per 1,000 requests) are both published by the gateway. Read them;
  never multiply one to get the other. A per-call charge (`costUsd`) has no
  per-1k twin, because a per-1k figure beside a payable amount invites a client
  to pay the wrong number.
- `provider` is always `AnyAPI`. A routing provider slug is never exposed. A
  lane's `source` name is a dataset brand or an anonymous animal, and is the
  only source identity that may appear.
- Canonical hosts only: `https://getanyapi.com` and `https://api.getanyapi.com`.
  Support is `support@getanyapi.com`.
- No em dash and no en dash glyphs. `scripts/check-dashes.sh` enforces it.

## Duplication that is deliberate

`_projection.py` and `_descriptions.py` are byte-identical across the three
packages. A fourth shared distribution to hold about 110 lines would add a
release to coordinate on every change, and would mean no package could be
installed on its own. The copies are the cheaper of the two costs.

## Gate

Each package gates on the same four commands, run from its own directory:

```
ruff check . && ruff format --check . && mypy && pytest
```

Unit tests pass with no network and no API key. Live tests are skipped unless
`ANYAPI_API_KEY` is set.

## Releasing

One workflow per package under `.github/workflows/`, triggered by a
package-prefixed tag such as `langchain-anyapi-v0.1.0`.

PyPI publication uses trusted publishing (OIDC, GitHub environment `pypi`) and
never falls back to a token, matching the convention in
`getanyapi-com/sdks/.github/workflows/release.yml`. If a release fails because
no trusted publisher is configured, configure the publisher. Do not add a
token.

## Getting a key

```
curl -s -X POST https://api.getanyapi.com/agent/signup \
  -H 'Content-Type: application/json' -d '{}'
```

returns a free trial key with starter credit and a per-key spend cap, with no
account and no dashboard. Set it as `ANYAPI_API_KEY`.
