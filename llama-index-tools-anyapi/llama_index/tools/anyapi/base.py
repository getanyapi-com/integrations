"""The AnyAPI tool spec: five tools over hundreds of data and scraping APIs.

AnyAPI publishes hundreds of SKUs. One tool per SKU would exhaust any agent's
context, so this spec exposes the AnyAPI MCP server's discovery-then-run loop
instead: search or list to find a SKU, get_api to read its strict input schema,
then run_api. Only run_api charges the USD wallet.
"""

from __future__ import annotations

from typing import Any

from getanyapi import AnyAPIError, RequestOptions
from llama_index.core.tools.tool_spec.base import BaseToolSpec

from ._client import LazyClients
from ._descriptions import GET_API, GET_BALANCE, LIST_APIS, RUN_API, SEARCH_APIS
from ._projection import (
    detail_dict,
    error_dict,
    run_dict,
    search_dict,
    summary_dict,
)

# Each entry pairs one blocking method with its awaitable twin, so a single
# tool carries a real AsyncAnyAPI path instead of the sync client on a thread.
_TOOLS: tuple[tuple[str, str], ...] = (
    ("search_apis", "asearch_apis"),
    ("list_apis", "alist_apis"),
    ("get_api", "aget_api"),
    ("run_api", "arun_api"),
    ("get_balance", "aget_balance"),
)


def _localize(text: str) -> str:
    """Point the shared wording at the tool names this package actually has.

    _descriptions.py is shared verbatim with the AnyAPI LangChain and Haystack
    packages, whose tools really are named anyapi_get_api, anyapi_run_api and
    so on. A LlamaIndex ToolSpec supplies that namespace itself, so its tools
    are named get_api and run_api, and the bare name is the only one a model
    can actually call. Every "anyapi_" in the shared text prefixes a tool name,
    so dropping the prefix is the whole translation, and the copied constants
    stay byte-identical to the template.
    """
    return text.replace("anyapi_", "")


def _options(
    fields: list[str] | None, max_items: int | None, summary: bool
) -> RequestOptions | None:
    """Response shaping for one run. None of it changes what is charged."""
    options: RequestOptions = {}
    if fields is not None:
        options["fields"] = fields
    if max_items is not None:
        options["max_items"] = max_items
    if summary:
        options["summary"] = summary
    return options or None


class AnyAPIToolSpec(BaseToolSpec):
    """Call the AnyAPI gateway from llama-index.

    Pass ``api_key`` or leave it unset to read ``ANYAPI_API_KEY`` from the
    environment. Neither the constructor nor ``to_tool_list`` needs a key or a
    network connection; a missing key surfaces as an error payload from the
    first tool that runs.
    """

    spec_functions: list[str | tuple[str, str]] = [*_TOOLS]

    def __init__(self, api_key: str | None = None) -> None:
        self._clients = LazyClients(api_key)

    def search_apis(
        self,
        query: str | None = None,
        category: str | None = None,
        platform: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        try:
            found = self._clients.sync_client().search(
                query=query, category=category, platform=platform, limit=limit
            )
        except AnyAPIError as exc:
            return error_dict(exc)
        return {
            "results": [search_dict(result) for result in found.results],
            "total": found.total,
            "ranking": found.ranking,
        }

    async def asearch_apis(
        self,
        query: str | None = None,
        category: str | None = None,
        platform: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        try:
            found = await self._clients.async_client().search(
                query=query, category=category, platform=platform, limit=limit
            )
        except AnyAPIError as exc:
            return error_dict(exc)
        return {
            "results": [search_dict(result) for result in found.results],
            "total": found.total,
            "ranking": found.ranking,
        }

    def list_apis(self, category: str | None = None) -> dict[str, Any]:
        try:
            entries = self._clients.sync_client().catalog(category=category)
        except AnyAPIError as exc:
            return error_dict(exc)
        return {
            "apis": [summary_dict(entry) for entry in entries],
            "total": len(entries),
        }

    async def alist_apis(self, category: str | None = None) -> dict[str, Any]:
        try:
            entries = await self._clients.async_client().catalog(category=category)
        except AnyAPIError as exc:
            return error_dict(exc)
        return {
            "apis": [summary_dict(entry) for entry in entries],
            "total": len(entries),
        }

    def get_api(self, sku_id: str) -> dict[str, Any]:
        try:
            entry = self._clients.sync_client().describe(sku_id)
        except AnyAPIError as exc:
            return error_dict(exc)
        return detail_dict(entry)

    async def aget_api(self, sku_id: str) -> dict[str, Any]:
        try:
            entry = await self._clients.async_client().describe(sku_id)
        except AnyAPIError as exc:
            return error_dict(exc)
        return detail_dict(entry)

    def run_api(
        self,
        sku_id: str,
        input: dict[str, Any],  # noqa: A002
        fields: list[str] | None = None,
        max_items: int | None = None,
        summary: bool = False,
    ) -> dict[str, Any]:
        try:
            result = self._clients.sync_client().run(
                sku_id, input, options=_options(fields, max_items, summary)
            )
        except AnyAPIError as exc:
            return error_dict(exc)
        return run_dict(result)

    async def arun_api(
        self,
        sku_id: str,
        input: dict[str, Any],  # noqa: A002
        fields: list[str] | None = None,
        max_items: int | None = None,
        summary: bool = False,
    ) -> dict[str, Any]:
        try:
            result = await self._clients.async_client().run(
                sku_id, input, options=_options(fields, max_items, summary)
            )
        except AnyAPIError as exc:
            return error_dict(exc)
        return run_dict(result)

    def get_balance(self) -> dict[str, Any]:
        try:
            balance = self._clients.sync_client().balance()
        except AnyAPIError as exc:
            return error_dict(exc)
        return {"usd": balance.usd}

    async def aget_balance(self) -> dict[str, Any]:
        try:
            balance = await self._clients.async_client().balance()
        except AnyAPIError as exc:
            return error_dict(exc)
        return {"usd": balance.usd}


# llama-index reads each tool's description and its per-parameter descriptions
# straight off the method docstring, and a docstring cannot be a runtime
# expression. Binding __doc__ after the class body is what lets the shared
# AnyAPI wording in _descriptions.py reach metadata.description unchanged.
# The Args block is Google style because that is what
# FunctionTool.extract_param_docs parses into the JSON schema.
_ARGS: dict[str, str] = {
    "search_apis": """

Args:
    query (Optional[str]): What to look for in the catalog, in plain words or keywords.
    category (Optional[str]): Restrict matches to one catalog category.
    platform (Optional[str]): Restrict matches to one platform id, such as reddit.
    limit (Optional[int]): Cap the matches returned. Default 25, maximum 50.
""",
    "list_apis": """

Args:
    category (Optional[str]): Restrict the browse to one catalog category.
""",
    "get_api": """

Args:
    sku_id (str): SKU slug of the API to describe, such as reddit.trending_posts.
""",
    "run_api": """

Args:
    sku_id (str): SKU slug of the API to run, such as reddit.trending_posts.
    input (dict): Request body, built from the input schema get_api returned.
    fields (Optional[list]): Keep only these keys of each result row.
    max_items (Optional[int]): Cap how many result rows come back.
    summary (bool): Return an outline of the result instead of the whole body.
""",
    "get_balance": "",
}

_DESCRIPTIONS: dict[str, str] = {
    "search_apis": SEARCH_APIS,
    "list_apis": LIST_APIS,
    "get_api": GET_API,
    "run_api": RUN_API,
    "get_balance": GET_BALANCE,
}

for _sync_name, _async_name in _TOOLS:
    _doc = _localize(_DESCRIPTIONS[_sync_name]) + _ARGS[_sync_name]
    getattr(AnyAPIToolSpec, _sync_name).__doc__ = _doc
    getattr(AnyAPIToolSpec, _async_name).__doc__ = _doc
