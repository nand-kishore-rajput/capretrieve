"""
Architectural invariant: the planner never imports connectors/ or
registry/.

This is one of the two invariants the project's entire premise rests on
("Every route back to 'LLM picks a tool by name' runs through one of
these two [invariants], and if either erodes, the project quietly becomes
RouterQueryEngine with extra steps"). This test makes it mechanically
enforced rather than just documented — it inspects actual import
statements in planner/*.py source files, not just current runtime
behavior, so a violation fails CI even if the offending import happens to
be unused at runtime.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PLANNER_DIR = Path(__file__).parents[2] / "src" / "capretrieve" / "planner"

FORBIDDEN_MODULE_PREFIXES = (
    "capretrieve.connectors",
    "capretrieve.registry",
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


def _all_planner_source_files() -> list[Path]:
    return sorted(PLANNER_DIR.rglob("*.py"))


@pytest.mark.parametrize("path", _all_planner_source_files(), ids=lambda p: str(p.relative_to(PLANNER_DIR)))
def test_planner_file_does_not_import_connectors_or_registry(path: Path):
    imports = _imported_modules(path)
    violations = [
        m for m in imports if any(m.startswith(prefix) for prefix in FORBIDDEN_MODULE_PREFIXES)
    ]
    assert not violations, (
        f"{path.relative_to(PLANNER_DIR.parents[1])} imports forbidden module(s): "
        f"{violations}. The planner must never import connectors/ or registry/ — "
        f"see this file's module docstring."
    )


def test_at_least_one_planner_file_was_actually_checked():
    """Guards against this test silently checking zero files if the
    planner directory structure changes."""
    assert len(_all_planner_source_files()) > 0