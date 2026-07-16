"""
Architectural invariant: fusion never calls an LLM.

This is what keeps fusion/ mechanically separate from generation/ — dedup
and score normalization are deterministic operations over Evidence
objects; only generation/synthesize.py is allowed to call an LLM after
retrieval. This test inspects actual import statements in fusion/*.py
source files via the AST, so it catches the violation even if an LLM
import were added but not yet exercised at runtime.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

FUSION_DIR = Path(__file__).parents[2] / "src" / "capretrieve" / "fusion"

FORBIDDEN_MODULE_PREFIXES = (
    "capretrieve.llm",
    "openai",
    "anthropic",
    "httpx",  # fusion should never make network calls of any kind
)


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def _all_fusion_source_files() -> list[Path]:
    return sorted(FUSION_DIR.rglob("*.py"))


@pytest.mark.parametrize(
    "path", _all_fusion_source_files(), ids=lambda p: str(p.relative_to(FUSION_DIR))
)
def test_fusion_file_does_not_import_llm_or_network_modules(path: Path):
    imports = _imported_modules(path)
    violations = [
        m for m in imports if any(m.startswith(prefix) for prefix in FORBIDDEN_MODULE_PREFIXES)
    ]
    assert not violations, (
        f"{path.relative_to(FUSION_DIR.parents[1])} imports forbidden module(s): "
        f"{violations}. fusion/ must never call an LLM or make network calls — "
        f"see this file's module docstring."
    )


def test_at_least_one_fusion_file_was_actually_checked():
    assert len(_all_fusion_source_files()) > 0