"""Errors raised while loading or validating capability manifests."""

from __future__ import annotations

from pathlib import Path


class ManifestError(Exception):
    """Base class for manifest loading/validation errors."""


class ManifestLoadError(ManifestError):
    """Raised when a manifest YAML file can't be read or parsed."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to load manifest from {path}: {reason}")


class ManifestValidationError(ManifestError):
    """Raised when a manifest YAML file doesn't satisfy CapabilityManifest."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Invalid manifest at {path}: {reason}")


class DuplicateConnectorIdError(ManifestError):
    """Raised when two manifest files declare the same connector_id."""

    def __init__(self, connector_id: str, first: Path, second: Path) -> None:
        self.connector_id = connector_id
        self.first = first
        self.second = second
        super().__init__(
            f"Duplicate connector_id '{connector_id}' declared in both "
            f"{first} and {second}"
        )