"""Haystack components for AnyAPI: one key, hundreds of data and scraping APIs, billed per request in USD.

Five components mirror the AnyAPI MCP server's discovery-then-run loop rather than
emitting one component per SKU, which would blow out any agent's context window.
"""

from ._client import AnyAPIComponent
from ._descriptions import (
    GET_API,
    GET_BALANCE,
    INSTRUCTIONS,
    LIST_APIS,
    RUN_API,
    SEARCH_APIS,
)
from .catalog import AnyAPIGetAPI, AnyAPIListAPIs, AnyAPISearchAPIs
from .run import AnyAPIGetBalance, AnyAPIRunAPI

__all__ = [
    "GET_API",
    "GET_BALANCE",
    "INSTRUCTIONS",
    "LIST_APIS",
    "RUN_API",
    "SEARCH_APIS",
    "AnyAPIComponent",
    "AnyAPIGetAPI",
    "AnyAPIGetBalance",
    "AnyAPIListAPIs",
    "AnyAPIRunAPI",
    "AnyAPISearchAPIs",
]
