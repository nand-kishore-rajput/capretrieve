"""
Tests that manifests load correctly from configs/connectors/*.yaml and
round-trip cleanly (YAML -> CapabilityManifest -> YAML -> CapabilityManifest
produces an identical object).

This is Phase 1's first exit criterion: "manifests round-trip to YAML and
back."
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from capretrieve.manifest.errors import (
    DuplicateConnectorIdError,
    ManifestLoadError,
    ManifestValidationError,
)
from capretrieve.manifest.loader import load_manifest_dir, load_manifest_file
from capretrieve.manifest.models import (
    CapabilityManifest,
    Freshness,
    Paradigm,
    PrivacyTier,
)

CONFIG_DIR = Path(__file__).parents[2] / "configs" / "connectors"


def test_loads_all_three_connectors():
    manifests = load_manifest_dir(CONFIG_DIR)
    assert set(manifests.keys()) == {"chroma", "obsidian", "web_search"}


def test_chroma_manifest_fields():
    manifests = load_manifest_dir(CONFIG_DIR)
    chroma = manifests["chroma"]
    assert chroma.paradigm == Paradigm.DENSE_SEMANTIC
    assert chroma.freshness == Freshness.INDEX_TIME
    assert chroma.privacy_tier == PrivacyTier.PRIVATE_LOCAL
    assert chroma.query_leaks_externally is False


def test_obsidian_manifest_fields():
    manifests = load_manifest_dir(CONFIG_DIR)
    obsidian = manifests["obsidian"]
    assert obsidian.paradigm == Paradigm.GRAPH_TRAVERSAL
    assert obsidian.freshness == Freshness.LIVE
    assert obsidian.privacy_tier == PrivacyTier.PRIVATE_LOCAL
    assert obsidian.query_leaks_externally is False


def test_web_search_manifest_fields():
    manifests = load_manifest_dir(CONFIG_DIR)
    web = manifests["web_search"]
    assert web.paradigm == Paradigm.KEYWORD
    assert web.freshness == Freshness.LIVE
    assert web.privacy_tier == PrivacyTier.PUBLIC_EXTERNAL
    # this is the field S1 (privacy hard-block) depends on
    assert web.query_leaks_externally is True


@pytest.mark.parametrize("connector_id", ["chroma", "obsidian", "web_search"])
def test_round_trip(connector_id: str):
    manifests = load_manifest_dir(CONFIG_DIR)
    original = manifests[connector_id]

    dumped = yaml.safe_dump(original.model_dump(mode="json"))
    reloaded = CapabilityManifest.model_validate(yaml.safe_load(dumped))

    assert reloaded == original


def test_missing_field_raises_validation_error(tmp_path):
    bad_yaml = tmp_path / "incomplete.yaml"
    bad_yaml.write_text("connector_id: broken\nparadigm: keyword\n")

    with pytest.raises(ManifestValidationError):
        load_manifest_file(bad_yaml)


def test_non_mapping_yaml_raises_load_error(tmp_path):
    bad_yaml = tmp_path / "list.yaml"
    bad_yaml.write_text("- just\n- a\n- list\n")

    with pytest.raises(ManifestLoadError):
        load_manifest_file(bad_yaml)


def test_duplicate_connector_id_raises(tmp_path):
    manifest_body = (
        "connector_id: dup\n"
        "paradigm: keyword\n"
        "freshness: static\n"
        "privacy_tier: private_local\n"
        "query_leaks_externally: false\n"
        "scope: test\n"
    )
    (tmp_path / "a.yaml").write_text(manifest_body)
    (tmp_path / "b.yaml").write_text(manifest_body)

    with pytest.raises(DuplicateConnectorIdError):
        load_manifest_dir(tmp_path)