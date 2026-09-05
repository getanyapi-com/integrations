"""The three free AnyAPI discovery components: search, browse, and describe.

None of these bills the wallet. Together they are the first half of the loop the
AnyAPI MCP server teaches: find a SKU, read its strict input schema, then run it.
"""

from __future__ import annotations

from typing import Any

from getanyapi import AnyAPIError, CatalogEntry, CatalogSearchResults
from haystack import component

from ._client import AnyAPIComponent
from ._projection import detail_dict, error_dict, search_dict, summary_dict


@component
class AnyAPISearchAPIs(AnyAPIComponent):
    """Rank the AnyAPI catalog against a query or a scope, keeping descriptions and omitting schemas.

    Free, never billed.

    Output sockets are split the way the gateway publishes them. ``results`` is the
    ranked list a pipeline feeds onward, and ``total`` is a separate fact rather than
    ``len(results)``: a relevance floor drops the weak tail and ``limit`` caps the list,
    so ``total`` counts relevant matches before the limit. ``ranking`` says whether
    meaning-based or substring matching served the search, which a caller may want to
    branch on. ``error`` is ``None`` on success and carries a readable payload otherwise,
    so a failed lookup does not abort the pipeline.
    """

    @component.output_types(
        results=list[dict[str, Any]],
        total=int,
        ranking=str | None,
        error=dict[str, Any] | None,
    )
    def run(
        self,
        query: str | None = None,
        category: str | None = None,
        platform: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Search the catalog.

        :param query: Optional. What the caller is looking for, matched against name, slug, and description.
            Pass at least one of ``query``, ``category``, or ``platform``: a scope on its own is a
            complete search, so ``category`` or ``platform`` with no ``query`` enumerates it.
        :param category: Optional category to narrow the search to.
        :param platform: Optional platform id to narrow the search to.
        :param limit: Optional cap on returned matches. The gateway default is 25 and its maximum is 50.
        :returns: The ranked ``results``, the ``total`` relevant matches, the ``ranking`` mode, and ``error``.
        """
        try:
            found = self.client().search(query=query, category=category, platform=platform, limit=limit)
        except AnyAPIError as exc:
            return _search_failed(exc)
        return _search_found(found)

    @component.output_types(
        results=list[dict[str, Any]],
        total=int,
        ranking=str | None,
        error=dict[str, Any] | None,
    )
    async def run_async(
        self,
        query: str | None = None,
        category: str | None = None,
        platform: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Search the catalog over the asynchronous SDK client.

        :param query: Optional. What the caller is looking for, matched against name, slug, and description.
            Pass at least one of ``query``, ``category``, or ``platform``: a scope on its own is a
            complete search, so ``category`` or ``platform`` with no ``query`` enumerates it.
        :param category: Optional category to narrow the search to.
        :param platform: Optional platform id to narrow the search to.
        :param limit: Optional cap on returned matches. The gateway default is 25 and its maximum is 50.
        :returns: The ranked ``results``, the ``total`` relevant matches, the ``ranking`` mode, and ``error``.
        """
        try:
            found = await self.async_client().search(query=query, category=category, platform=platform, limit=limit)
        except AnyAPIError as exc:
            return _search_failed(exc)
        return _search_found(found)


def _search_found(found: CatalogSearchResults) -> dict[str, Any]:
    return {
        "results": [search_dict(result) for result in found.results],
        "total": found.total,
        "ranking": found.ranking,
        "error": None,
    }


def _search_failed(exc: AnyAPIError) -> dict[str, Any]:
    return {"results": [], "total": 0, "ranking": None, "error": error_dict(exc)}


@component
class AnyAPIListAPIs(AnyAPIComponent):
    """Browse the catalog as lightweight summaries: id, name, category, and USD pricing.

    Free, never billed.

    One list socket, because the gateway publishes a bare list here and ``len(apis)``
    is not a second fact worth a socket of its own. ``error`` is ``None`` on success.
    """

    @component.output_types(apis=list[dict[str, Any]], error=dict[str, Any] | None)
    def run(self, category: str | None = None) -> dict[str, Any]:
        """Browse the catalog.

        :param category: Optional category to filter by. Omit it to browse everything.
        :returns: The ``apis`` summaries and ``error``.
        """
        try:
            entries = self.client().catalog(category=category)
        except AnyAPIError as exc:
            return _list_failed(exc)
        return _list_found(entries)

    @component.output_types(apis=list[dict[str, Any]], error=dict[str, Any] | None)
    async def run_async(self, category: str | None = None) -> dict[str, Any]:
        """Browse the catalog over the asynchronous SDK client.

        :param category: Optional category to filter by. Omit it to browse everything.
        :returns: The ``apis`` summaries and ``error``.
        """
        try:
            entries = await self.async_client().catalog(category=category)
        except AnyAPIError as exc:
            return _list_failed(exc)
        return _list_found(entries)


def _list_found(entries: list[CatalogEntry]) -> dict[str, Any]:
    return {"apis": [summary_dict(entry) for entry in entries], "error": None}


def _list_failed(exc: AnyAPIError) -> dict[str, Any]:
    return {"apis": [], "error": error_dict(exc)}


@component
class AnyAPIGetAPI(AnyAPIComponent):
    """Get one API in full: strict input schema, output schema, per-lane USD pricing, and latency.

    Free, never billed.

    Three sockets, one per documented downstream use. ``api`` is the whole definition
    for a prompt or a log. ``input_schema`` is lifted out because it is the input to the
    very next step of the loop, ``AnyAPIRunAPI``, and building the input from anything
    else usually fails. ``pricing`` is lifted out because ``pricing.from.maxUsd`` and
    ``pricing.failoverMaxUsd`` are what a caller reads to bound spend before running.
    Neither is recomputed: both are the same values already inside ``api``.
    """

    @component.output_types(
        api=dict[str, Any] | None,
        input_schema=dict[str, Any] | None,
        pricing=dict[str, Any] | None,
        error=dict[str, Any] | None,
    )
    def run(self, slug: str) -> dict[str, Any]:
        """Describe one API.

        :param slug: The SKU id, for example ``reddit.trending_posts``.
        :returns: The full ``api`` definition, its ``input_schema``, its ``pricing``, and ``error``.
        """
        try:
            entry = self.client().describe(slug)
        except AnyAPIError as exc:
            return _get_failed(exc)
        return _get_found(entry)

    @component.output_types(
        api=dict[str, Any] | None,
        input_schema=dict[str, Any] | None,
        pricing=dict[str, Any] | None,
        error=dict[str, Any] | None,
    )
    async def run_async(self, slug: str) -> dict[str, Any]:
        """Describe one API over the asynchronous SDK client.

        :param slug: The SKU id, for example ``reddit.trending_posts``.
        :returns: The full ``api`` definition, its ``input_schema``, its ``pricing``, and ``error``.
        """
        try:
            entry = await self.async_client().describe(slug)
        except AnyAPIError as exc:
            return _get_failed(exc)
        return _get_found(entry)


def _get_found(entry: CatalogEntry) -> dict[str, Any]:
    detail = detail_dict(entry)
    return {
        "api": detail,
        "input_schema": detail["inputSchema"],
        "pricing": detail["pricing"],
        "error": None,
    }


def _get_failed(exc: AnyAPIError) -> dict[str, Any]:
    return {"api": None, "input_schema": None, "pricing": None, "error": error_dict(exc)}
