"""Errors raised while registering or looking up connectors."""

from __future__ import annotations


class RegistryError(Exception):
    """Base class for registry errors."""


class UnknownConnectorIdError(RegistryError):
    """Raised when registering a connector whose id has no loaded manifest."""

    def __init__(self, connector_id: str, known: set[str]) -> None:
        self.connector_id = connector_id
        self.known = known
        super().__init__(
            f"No manifest loaded for connector_id '{connector_id}'. "
            f"Known connector ids: {sorted(known)}. "
            f"Add a matching YAML file to configs/connectors/ first."
        )


class ManifestConnectorMismatchError(RegistryError):
    """Raised when a connector's manifest() disagrees with the loaded
    manifest for the same connector_id."""

    def __init__(self, connector_id: str) -> None:
        self.connector_id = connector_id
        super().__init__(
            f"Connector '{connector_id}' returned a manifest() that does "
            f"not match the manifest loaded from configs/connectors/. "
            f"The YAML file and the connector implementation have drifted "
            f"apart."
        )


class ConnectorNotRegisteredError(RegistryError):
    """Raised when looking up a connector_id that has no registered
    connector instance (manifest may exist, but nothing implements it)."""

    def __init__(self, connector_id: str, registered: set[str]) -> None:
        self.connector_id = connector_id
        self.registered = registered
        super().__init__(
            f"No connector registered for '{connector_id}'. "
            f"Registered connector ids: {sorted(registered)}."
        )