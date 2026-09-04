"""The five AnyAPI tools, ready to hand to a Haystack ``Agent``.

An ``Agent`` consumes tools, not pipeline sockets, so each component is wrapped in a
``ComponentTool`` subclass that fixes the tool name and carries the MCP server's own
description. A ``Tool`` serializes into a ``{"type": ..., "data": {...}}`` envelope,
which is not the ``{"type": ..., "init_parameters": {...}}`` envelope a ``Component``
uses. Subclasses keep that envelope down to the one thing a caller sets, the key.
"""

from __future__ import annotations

from typing import Any, TypeVar, cast

from haystack.core.serialization import generate_qualified_class_name
from haystack.tools import ComponentTool
from haystack.utils import Secret, deserialize_secrets_inplace

from haystack_integrations.components.connectors.anyapi import (
    GET_API,
    GET_BALANCE,
    LIST_APIS,
    RUN_API,
    SEARCH_APIS,
    AnyAPIComponent,
    AnyAPIGetAPI,
    AnyAPIGetBalance,
    AnyAPIListAPIs,
    AnyAPIRunAPI,
    AnyAPISearchAPIs,
)

T = TypeVar("T", bound="_AnyAPITool")


class _AnyAPITool(ComponentTool):
    """Base wrapper: a fixed name and description, and a key-only serialization envelope."""

    def __init__(self, wrapped: AnyAPIComponent, name: str, description: str, api_key: Secret) -> None:
        self.api_key = api_key
        super().__init__(component=cast(Any, wrapped), name=name, description=description)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the tool, keeping the key as a ``Secret`` reference rather than a value.

        :returns: A Haystack tool dictionary.
        """
        return {
            "type": generate_qualified_class_name(type(self)),
            "data": {"api_key": self.api_key.to_dict()},
        }

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        """Rebuild a tool from its serialized form.

        :param data: The dictionary produced by :meth:`to_dict`.
        :returns: The deserialized tool.
        """
        deserialize_secrets_inplace(data["data"], keys=["api_key"])
        return cls(**data["data"])


class AnyAPISearchAPIsTool(_AnyAPITool):
    """``anyapi_search_apis``: ranked catalog search. Free, never billed."""

    def __init__(self, api_key: Secret = Secret.from_env_var("ANYAPI_API_KEY")) -> None:
        """
        :param api_key: The AnyAPI key, read from ``ANYAPI_API_KEY`` by default.
        """
        super().__init__(AnyAPISearchAPIs(api_key=api_key), "anyapi_search_apis", SEARCH_APIS, api_key)


class AnyAPIListAPIsTool(_AnyAPITool):
    """``anyapi_list_apis``: browse the catalog as summaries. Free, never billed."""

    def __init__(self, api_key: Secret = Secret.from_env_var("ANYAPI_API_KEY")) -> None:
        """
        :param api_key: The AnyAPI key, read from ``ANYAPI_API_KEY`` by default.
        """
        super().__init__(AnyAPIListAPIs(api_key=api_key), "anyapi_list_apis", LIST_APIS, api_key)


class AnyAPIGetAPITool(_AnyAPITool):
    """``anyapi_get_api``: one API in full, including its strict input schema. Free, never billed."""

    def __init__(self, api_key: Secret = Secret.from_env_var("ANYAPI_API_KEY")) -> None:
        """
        :param api_key: The AnyAPI key, read from ``ANYAPI_API_KEY`` by default.
        """
        super().__init__(AnyAPIGetAPI(api_key=api_key), "anyapi_get_api", GET_API, api_key)


class AnyAPIRunAPITool(_AnyAPITool):
    """``anyapi_run_api``: execute one SKU. This is the tool that spends the USD wallet."""

    def __init__(self, api_key: Secret = Secret.from_env_var("ANYAPI_API_KEY")) -> None:
        """
        :param api_key: The AnyAPI key, read from ``ANYAPI_API_KEY`` by default.
        """
        super().__init__(AnyAPIRunAPI(api_key=api_key), "anyapi_run_api", RUN_API, api_key)


class AnyAPIGetBalanceTool(_AnyAPITool):
    """``anyapi_get_balance``: the remaining wallet balance in USD. Free, never charged."""

    def __init__(self, api_key: Secret = Secret.from_env_var("ANYAPI_API_KEY")) -> None:
        """
        :param api_key: The AnyAPI key, read from ``ANYAPI_API_KEY`` by default.
        """
        super().__init__(AnyAPIGetBalance(api_key=api_key), "anyapi_get_balance", GET_BALANCE, api_key)


def anyapi_tools(api_key: Secret = Secret.from_env_var("ANYAPI_API_KEY")) -> list[ComponentTool]:
    """Build all five AnyAPI tools, in the order the discovery-then-run loop uses them.

    :param api_key: The AnyAPI key, read from ``ANYAPI_API_KEY`` by default. No key is
        resolved here; a missing key surfaces only when a tool is actually called.
    :returns: The search, list, get, run, and balance tools.
    """
    return [
        AnyAPISearchAPIsTool(api_key=api_key),
        AnyAPIListAPIsTool(api_key=api_key),
        AnyAPIGetAPITool(api_key=api_key),
        AnyAPIRunAPITool(api_key=api_key),
        AnyAPIGetBalanceTool(api_key=api_key),
    ]
