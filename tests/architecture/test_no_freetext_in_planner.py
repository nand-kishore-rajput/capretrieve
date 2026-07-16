"""
Architectural invariant: manifest.scope is never read by planner code.

`scope` is documentation only (see manifest/models.py). The moment
planner code reads it, the project has rebuilt prose-based routing
(RouterQueryEngine) with extra steps. This test inspects actual attribute
access in planner/*.py source files via the AST, so it catches the
violation even if `.scope` access happens to be on an unrelated object
that merely shares the attribute name in a way that isn't exercised by
current tests — flagging false positives for manual review is an
acceptable cost for not missing a real violation.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PLANNER_DIR = Path(__file__).parents[2] / "src" / "capretrieve" / "planner"


def _accesses_scope_attribute(path: Path) -> bool:
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "scope":
            return True
    return False


def _all_planner_source_files() -> list[Path]:
    return sorted(PLANNER_DIR.rglob("*.py"))


@pytest.mark.parametrize(
    "path", _all_planner_source_files(), ids=lambda p: str(p.relative_to(PLANNER_DIR))
)
def test_planner_file_does_not_access_scope_attribute(path: Path):
    assert not _accesses_scope_attribute(path), (
        f"{path.relative_to(PLANNER_DIR.parents[1])} accesses a `.scope` "
        f"attribute. manifest.scope is documentation-only and must never "
        f"be read by planner code — see this file's module docstring."
    )


def test_at_least_one_planner_file_was_actually_checked():
    assert len(_all_planner_source_files()) > 0