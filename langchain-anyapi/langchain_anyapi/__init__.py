"""LangChain tools for AnyAPI.

AnyAPI is one key and one USD wallet in front of hundreds of data and scraping
APIs. This package exposes the AnyAPI discovery then run loop as five LangChain
tools, plus a toolkit that hands an agent all five at once.
"""

from ._descriptions import INSTRUCTIONS as ANYAPI_INSTRUCTIONS
from ._version import __version__
from .toolkit import AnyAPIToolkit
from .tools import (
    AnyAPIGetAPI,
    AnyAPIGetBalance,
    AnyAPIListAPIs,
    AnyAPIRunAPI,
    AnyAPISearchAPIs,
    GetAPIInput,
    GetBalanceInput,
    ListAPIsInput,
    RunAPIInput,
    SearchAPIsInput,
)

__all__ = [
    "ANYAPI_INSTRUCTIONS",
    "AnyAPIGetAPI",
    "AnyAPIGetBalance",
    "AnyAPIListAPIs",
    "AnyAPIRunAPI",
    "AnyAPISearchAPIs",
    "AnyAPIToolkit",
    "GetAPIInput",
    "GetBalanceInput",
    "ListAPIsInput",
    "RunAPIInput",
    "SearchAPIsInput",
    "__version__",
]
