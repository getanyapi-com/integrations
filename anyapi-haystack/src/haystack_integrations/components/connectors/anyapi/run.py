"""The billed AnyAPI run component and the free wallet balance component."""

from __future__ import annotations

from typing import Any

from getanyapi import AnyAPIError, Balance, RequestOptions, RunResult
from haystack import component

from ._client import PROVIDER, AnyAPIComponent
from ._projection import error_dict, run_dict


@component
class AnyAPIRunAPI(AnyAPIComponent):
    """Execute one AnyAPI SKU with a normalized input payload. This is the component that spends.

    Charges the USD wallet on success only, and reports the actual ``cost_usd`` of the call.

    The billed envelope is split into sockets instead of handed on as one blob, because a
    pipeline connects each part to a different place: ``data`` goes to whatever consumes the
    payload, ``found`` is the branch a router reads, ``cost_usd`` and ``items`` go to a spend
    or volume guard, and ``result_id`` is the handle for support and replay. A single blob
    would force every one of those consumers to parse the same dictionary again. ``provider``
    is always the literal ``AnyAPI``. Every value comes off the wire unscaled. On failure the
    unknowable sockets are ``None`` rather than a fabricated zero, and ``error`` carries a
    readable payload so the pipeline can recover instead of aborting.
    """

    @component.output_types(
        data=Any,
        found=bool | None,
        cost_usd=float | None,
        items=int | None,
        provider=str,
        result_id=str | None,
        error=dict[str, Any] | None,
    )
    def run(
        self,
        slug: str,
        input: dict[str, Any],
        fields: list[str] | None = None,
        max_items: int | None = None,
        summary: bool = False,
    ) -> dict[str, Any]:
        """Run one API.

        :param slug: The SKU id, for example ``reddit.trending_posts``.
        :param input: The normalized input payload. Read the strict schema from
            ``AnyAPIGetAPI`` first: unknown fields are rejected, not ignored.
        :param fields: Optional keys to keep in the response. Response shaping never changes the charge.
        :param max_items: Optional cap on returned rows. Response shaping never changes the charge.
        :param summary: Return an outline only. Response shaping never changes the charge.
        :returns: The ``data``, ``found``, ``cost_usd``, ``items``, ``provider``, ``result_id``, and ``error``.
        """
        try:
            result = self.client().run(slug, input, options=_options(fields, max_items, summary))
        except AnyAPIError as exc:
            return _run_failed(exc)
        return _run_finished(result)

    @component.output_types(
        data=Any,
        found=bool | None,
        cost_usd=float | None,
        items=int | None,
        provider=str,
        result_id=str | None,
        error=dict[str, Any] | None,
    )
    async def run_async(
        self,
        slug: str,
        input: dict[str, Any],
        fields: list[str] | None = None,
        max_items: int | None = None,
        summary: bool = False,
    ) -> dict[str, Any]:
        """Run one API over the asynchronous SDK client.

        :param slug: The SKU id, for example ``reddit.trending_posts``.
        :param input: The normalized input payload. Read the strict schema from
            ``AnyAPIGetAPI`` first: unknown fields are rejected, not ignored.
        :param fields: Optional keys to keep in the response. Response shaping never changes the charge.
        :param max_items: Optional cap on returned rows. Response shaping never changes the charge.
        :param summary: Return an outline only. Response shaping never changes the charge.
        :returns: The ``data``, ``found``, ``cost_usd``, ``items``, ``provider``, ``result_id``, and ``error``.
        """
        try:
            result = await self.async_client().run(slug, input, options=_options(fields, max_items, summary))
        except AnyAPIError as exc:
            return _run_failed(exc)
        return _run_finished(result)


def _options(fields: list[str] | None, max_items: int | None, summary: bool) -> RequestOptions | None:
    options: RequestOptions = {}
    if fields is not None:
        options["fields"] = fields
    if max_items is not None:
        options["max_items"] = max_items
    if summary:
        options["summary"] = summary
    return options or None


def _run_finished(result: RunResult[Any]) -> dict[str, Any]:
    envelope = run_dict(result)
    return {
        "data": envelope["data"],
        "found": envelope["found"],
        "cost_usd": envelope["costUsd"],
        "items": envelope["items"],
        "provider": envelope["provider"],
        "result_id": envelope["resultId"],
        "error": None,
    }


def _run_failed(exc: AnyAPIError) -> dict[str, Any]:
    return {
        "data": None,
        "found": None,
        "cost_usd": None,
        "items": None,
        "provider": PROVIDER,
        "result_id": None,
        "error": error_dict(exc),
    }


@component
class AnyAPIGetBalance(AnyAPIComponent):
    """Report the remaining AnyAPI wallet balance in USD. Free, never charged.

    ``usd`` is the only fact the gateway publishes here. It is ``None`` rather than
    ``0.0`` when the call failed, because an unknown balance is not an empty one.
    """

    @component.output_types(usd=float | None, error=dict[str, Any] | None)
    def run(self) -> dict[str, Any]:
        """Read the wallet balance.

        :returns: The remaining balance in ``usd`` and ``error``.
        """
        try:
            balance = self.client().balance()
        except AnyAPIError as exc:
            return _balance_failed(exc)
        return _balance_found(balance)

    @component.output_types(usd=float | None, error=dict[str, Any] | None)
    async def run_async(self) -> dict[str, Any]:
        """Read the wallet balance over the asynchronous SDK client.

        :returns: The remaining balance in ``usd`` and ``error``.
        """
        try:
            balance = await self.async_client().balance()
        except AnyAPIError as exc:
            return _balance_failed(exc)
        return _balance_found(balance)


def _balance_found(balance: Balance) -> dict[str, Any]:
    return {"usd": balance.usd, "error": None}


def _balance_failed(exc: AnyAPIError) -> dict[str, Any]:
    return {"usd": None, "error": error_dict(exc)}
