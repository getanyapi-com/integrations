"""The five AnyAPI tools: search, list, get, run, and balance.

Five tools rather than one per SKU. AnyAPI publishes hundreds of APIs, and a
tool per SKU would not fit an agent's context. These five are the discovery
then run loop the AnyAPI MCP server already proves: search or list to find a
SKU, get_api to read its strict input schema, then run_api.
"""

from __future__ import annotations

from typing import Any

from getanyapi import AnyAPI, AsyncAnyAPI
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from pydantic import BaseModel, Field

from ._client import AnyAPIToolBase, run_options
from ._descriptions import GET_API, GET_BALANCE, LIST_APIS, RUN_API, SEARCH_APIS
from ._projection import detail_dict, run_dict, search_dict, summary_dict


class SearchAPIsInput(BaseModel):
    """Arguments for a ranked search over the AnyAPI catalog."""

    query: str = Field(
        description="What you need data about, matched by meaning and keyword "
        "across each API's name, slug, and description. For example "
        "'reddit trending posts' or 'find a work email address'."
    )
    category: str | None = Field(
        default=None,
        description="Optional. Keep only APIs in this catalog category, "
        "spelled exactly as a previous result's `category`.",
    )
    platform: str | None = Field(
        default=None,
        description="Optional. Keep only APIs for this platform, spelled "
        "exactly as a previous result's `platform`, for example 'reddit'.",
    )
    limit: int | None = Field(
        default=None,
        description="Optional. Cap the number of matches returned. The "
        "default is 25 and the maximum is 50.",
    )


class ListAPIsInput(BaseModel):
    """Arguments for browsing catalog summaries."""

    category: str | None = Field(
        default=None,
        description="Optional. Browse only this catalog category, spelled "
        "exactly as a previous result's `category`. Omit for the whole "
        "catalog.",
    )


class GetAPIInput(BaseModel):
    """Arguments for reading one API's full definition."""

    sku_id: str = Field(
        description="The SKU id of the API, taken from the `id` of a search "
        "or list result, for example 'reddit.trending_posts'."
    )


class RunAPIInput(BaseModel):
    """Arguments for one billed run of an API."""

    sku_id: str = Field(
        description="The SKU id of the API to run, taken from the `id` of a "
        "search or list result, for example 'reddit.trending_posts'."
    )
    input: dict[str, Any] = Field(
        description="The request payload, built from this SKU's `inputSchema` "
        "as returned by anyapi_get_api. Every schema is strict: an unknown "
        "field is rejected, not ignored, and sibling APIs use different field "
        "names."
    )
    fields: list[str] | None = Field(
        default=None,
        description="Optional. Keep only these top-level keys of each result "
        "row, to keep a large response out of your context. Does not change "
        "what you are charged.",
    )
    max_items: int | None = Field(
        default=None,
        description="Optional. Return at most this many result rows. Does not "
        "change what you are charged.",
    )
    summary: bool | None = Field(
        default=None,
        description="Optional. Return an outline of the response instead of "
        "the whole thing. Does not change what you are charged.",
    )


class GetBalanceInput(BaseModel):
    """Arguments for reading the wallet balance. There are none."""


class AnyAPISearchAPIs(AnyAPIToolBase):
    """Ranked catalog search. Free, and it never touches the wallet."""

    name: str = "anyapi_search_apis"
    description: str = SEARCH_APIS
    args_schema: type[BaseModel] = SearchAPIsInput

    def _run(
        self,
        query: str,
        category: str | None = None,
        platform: str | None = None,
        limit: int | None = None,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> dict[str, Any]:
        def call(client: AnyAPI) -> dict[str, Any]:
            found = client.search(
                query=query, category=category, platform=platform, limit=limit
            )
            return {
                "results": [search_dict(r) for r in found.results],
                "total": found.total,
                "ranking": found.ranking,
            }

        return self.call(call)

    async def _arun(
        self,
        query: str,
        category: str | None = None,
        platform: str | None = None,
        limit: int | None = None,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> dict[str, Any]:
        async def call(client: AsyncAnyAPI) -> dict[str, Any]:
            found = await client.search(
                query=query, category=category, platform=platform, limit=limit
            )
            return {
                "results": [search_dict(r) for r in found.results],
                "total": found.total,
                "ranking": found.ranking,
            }

        return await self.acall(call)


class AnyAPIListAPIs(AnyAPIToolBase):
    """Browse-weight catalog summaries. Free, and it never touches the wallet."""

    name: str = "anyapi_list_apis"
    description: str = LIST_APIS
    args_schema: type[BaseModel] = ListAPIsInput

    def _run(
        self,
        category: str | None = None,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> dict[str, Any]:
        def call(client: AnyAPI) -> dict[str, Any]:
            entries = client.catalog(category=category)
            return {"apis": [summary_dict(e) for e in entries]}

        return self.call(call)

    async def _arun(
        self,
        category: str | None = None,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> dict[str, Any]:
        async def call(client: AsyncAnyAPI) -> dict[str, Any]:
            entries = await client.catalog(category=category)
            return {"apis": [summary_dict(e) for e in entries]}

        return await self.acall(call)


class AnyAPIGetAPI(AnyAPIToolBase):
    """One API in full, schemas included. Free, and it never touches the wallet."""

    name: str = "anyapi_get_api"
    description: str = GET_API
    args_schema: type[BaseModel] = GetAPIInput

    def _run(
        self,
        sku_id: str,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> dict[str, Any]:
        def call(client: AnyAPI) -> dict[str, Any]:
            return detail_dict(client.describe(sku_id))

        return self.call(call)

    async def _arun(
        self,
        sku_id: str,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> dict[str, Any]:
        async def call(client: AsyncAnyAPI) -> dict[str, Any]:
            return detail_dict(await client.describe(sku_id))

        return await self.acall(call)


class AnyAPIRunAPI(AnyAPIToolBase):
    """Execute one API. This is the tool that charges the USD wallet."""

    name: str = "anyapi_run_api"
    description: str = RUN_API
    args_schema: type[BaseModel] = RunAPIInput

    def _run(
        self,
        sku_id: str,
        input: dict[str, Any],
        fields: list[str] | None = None,
        max_items: int | None = None,
        summary: bool | None = None,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> dict[str, Any]:
        options = run_options(fields, max_items, summary)

        def call(client: AnyAPI) -> dict[str, Any]:
            return run_dict(client.run(sku_id, input, options=options))

        return self.call(call)

    async def _arun(
        self,
        sku_id: str,
        input: dict[str, Any],
        fields: list[str] | None = None,
        max_items: int | None = None,
        summary: bool | None = None,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> dict[str, Any]:
        options = run_options(fields, max_items, summary)

        async def call(client: AsyncAnyAPI) -> dict[str, Any]:
            return run_dict(await client.run(sku_id, input, options=options))

        return await self.acall(call)


class AnyAPIGetBalance(AnyAPIToolBase):
    """Remaining wallet balance in USD. Free, and it never touches the wallet."""

    name: str = "anyapi_get_balance"
    description: str = GET_BALANCE
    args_schema: type[BaseModel] = GetBalanceInput

    def _run(
        self,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> dict[str, Any]:
        def call(client: AnyAPI) -> dict[str, Any]:
            return {"usd": client.balance().usd}

        return self.call(call)

    async def _arun(
        self,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> dict[str, Any]:
        async def call(client: AsyncAnyAPI) -> dict[str, Any]:
            balance = await client.balance()
            return {"usd": balance.usd}

        return await self.acall(call)
