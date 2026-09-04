"""The five AnyAPI tools for a Haystack ``Agent``, plus the AnyAPI system instructions."""

from haystack_integrations.components.connectors.anyapi import INSTRUCTIONS as ANYAPI_INSTRUCTIONS

from .tools import (
    AnyAPIGetAPITool,
    AnyAPIGetBalanceTool,
    AnyAPIListAPIsTool,
    AnyAPIRunAPITool,
    AnyAPISearchAPIsTool,
    anyapi_tools,
)

__all__ = [
    "ANYAPI_INSTRUCTIONS",
    "AnyAPIGetAPITool",
    "AnyAPIGetBalanceTool",
    "AnyAPIListAPIsTool",
    "AnyAPIRunAPITool",
    "AnyAPISearchAPIsTool",
    "anyapi_tools",
]
