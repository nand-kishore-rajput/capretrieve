"""
Architectural invariant: planner/models/ imports only manifest/ and
stdlib.

planner/models/ (QueryRequirements, ExecutionPlan, PlanStep,
SelectionDecision) is meant to be pure data — no LLM calls, no
connector/registry knowledge, not even the rest of planner/'s own logic
modules (constraints.py, scoring.py, etc.). This keeps the data contract
inspectable and reusable independent of the planning algorithm built on
top of it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

MODELS_DIR = Path(__file__).parents[2] / "src" / "capretrieve" / "planner" / "models"

ALLOWED_CAPRETRIEVE_PREFIXES = ("capretrieve.manifest",)

# stdlib modules these files are expected to plausibly use; anything
# starting with "capretrieve." not in ALLOWED_CAPRETRIEVE_PREFIXES is a
# violation. Third-party (e.g. pydantic) is allowed — the "pure" claim is
# about internal architecture boundaries, not zero dependencies.


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def _all_model_source_files() -> list[Path]:
    return sorted(MODELS_DIR.rglob("*.py"))


@pytest.mark.parametrize(
    "path", _all_model_source_files(), ids=lambda p: str(p.relative_to(MODELS_DIR))
)
def test_model_file_imports_only_manifest_or_external(path: Path):
    imports = _imported_modules(path)
    violations = [
        m
        for m in imports
        if m.startswith("capretrieve.")
        and not any(m.startswith(prefix) for prefix in ALLOWED_CAPRETRIEVE_PREFIXES)
        and not m.startswith("capretrieve.planner.models")  # models may import each other
    ]
    assert not violations, (
        f"{path.relative_to(MODELS_DIR.parents[2])} imports forbidden internal "
        f"module(s): {violations}. planner/models/ must import only manifest/ "
        f"(and other planner/models/ files) + stdlib/third-party — see this "
        f"file's module docstring."
    )


def test_at_least_one_model_file_was_actually_checked():
    assert len(_all_model_source_files()) > 0