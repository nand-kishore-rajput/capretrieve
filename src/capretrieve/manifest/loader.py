"""
Load CapabilityManifest objects from YAML files.

This is the only place raw YAML is parsed into manifests. registry/static.py
calls load_manifest_dir() at startup; nothing else should read
configs/connectors/*.yaml directly.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from capretrieve.manifest.errors import (
    DuplicateConnectorIdError,
    ManifestLoadError,
    ManifestValidationError,
)
from capretrieve.manifest.models import CapabilityManifest


def load_manifest_file(path: Path) -> CapabilityManifest:
    """Load and validate a single manifest YAML file."""
    try:
        raw = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise ManifestLoadError(path, str(exc)) from exc

    if not isinstance(raw, dict):
        raise ManifestLoadError(path, "top-level YAML content must be a mapping")

    try:
        return CapabilityManifest(**raw)
    except ValidationError as exc:
        raise ManifestValidationError(path, str(exc)) from exc


def load_manifest_dir(config_dir: Path) -> dict[str, CapabilityManifest]:
    """
    Load every *.yaml file in config_dir into a dict keyed by connector_id.

    Raises DuplicateConnectorIdError if two files declare the same
    connector_id — that's a configuration bug, not something to silently
    resolve by last-write-wins.
    """
    manifests: dict[str, CapabilityManifest] = {}
    sources: dict[str, Path] = {}

    for path in sorted(config_dir.glob("*.yaml")):
        manifest = load_manifest_file(path)
        if manifest.connector_id in manifests:
            raise DuplicateConnectorIdError(
                manifest.connector_id, sources[manifest.connector_id], path
            )
        manifests[manifest.connector_id] = manifest
        sources[manifest.connector_id] = path

    return manifests