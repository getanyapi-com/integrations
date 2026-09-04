"""Key handling and lazy AnyAPI client ownership shared by every component here.

The clients are built on first call rather than in ``__init__`` so that importing
this package never needs a key and constructing a component never opens a socket.
``Secret.resolve_value`` is therefore not called until a component actually runs.
"""

from __future__ import annotations

from typing import Any, TypeVar

from getanyapi import AnyAPI, AsyncAnyAPI
from haystack import default_from_dict, default_to_dict
from haystack.utils import Secret, deserialize_secrets_inplace

#: AnyAPI is the top-level customer-facing provider. A routing provider slug is never exposed.
PROVIDER = "AnyAPI"

T = TypeVar("T", bound="AnyAPIComponent")


class AnyAPIComponent:
    """Base for the AnyAPI components: the key, the lazy clients, and the ``Secret`` round trip.

    :param api_key: The AnyAPI key. Read from the ``ANYAPI_API_KEY`` environment
        variable by default and resolved on first call, never at construction.
    """

    def __init__(self, api_key: Secret = Secret.from_env_var("ANYAPI_API_KEY")) -> None:
        self.api_key = api_key
        self._client: AnyAPI | None = None
        self._async_client: AsyncAnyAPI | None = None

    def client(self) -> AnyAPI:
        """Build the synchronous SDK client on first use and reuse it afterwards.

        :returns: The shared ``getanyapi.AnyAPI`` client for this component.
        """
        if self._client is None:
            self._client = AnyAPI(api_key=self.api_key.resolve_value())
        return self._client

    def async_client(self) -> AsyncAnyAPI:
        """Build the asynchronous SDK client on first use and reuse it afterwards.

        :returns: The shared ``getanyapi.AsyncAnyAPI`` client for this component.
        """
        if self._async_client is None:
            self._async_client = AsyncAnyAPI(api_key=self.api_key.resolve_value())
        return self._async_client

    def to_dict(self) -> dict[str, Any]:
        """Serialize the component, keeping the key as a ``Secret`` reference rather than a value.

        :returns: A Haystack component dictionary.
        """
        return default_to_dict(self, api_key=self.api_key.to_dict())

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        """Rebuild a component from its serialized form.

        :param data: The dictionary produced by :meth:`to_dict`.
        :returns: The deserialized component.
        """
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        return default_from_dict(cls, data)
