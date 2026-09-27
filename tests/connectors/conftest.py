"""
Shared fixtures for connector tests.

`sample_vault` writes a small, purpose-built Obsidian vault into tmp_path.
Connector unit tests run against it instead of fixtures/data/vault, so the
demo/scenario vault can change freely without breaking contract tests.

Graph shape (undirected for traversal):

    Project Retrospective --[[ ]]--> Standing Desk
    Project Retrospective --[[ ]]--> Sprint Planning
    Sprint Planning       --[[ ]]--> Project Retrospective   (backlink)
    Intermittent Fasting                                      (isolated)

Features each note exists to exercise:
- Project Retrospective: frontmatter tags (work, retrospective), outgoing links
- Sprint Planning:       backlink source for Project Retrospective
- Standing Desk:         frontmatter + inline #health (dedup), no outgoing links
- Intermittent Fasting:  isolated node, unique keywords, "16:8" in body
"""

from __future__ import annotations

from pathlib import Path

import pytest

SAMPLE_VAULT_NOTES: dict[str, str] = {
    "Project Retrospective": """---
tags: [work, retrospective]
date: 2025-02-10
---

# Project Retrospective

What went well this quarter. Moving to a [[Standing Desk]] helped with
long review sessions. Estimation was still off, see [[Sprint Planning]].
""",
    "Sprint Planning": """---
tags: [work]
---

# Sprint Planning

Break stories down before committing. Revisit the outcomes captured in
[[Project Retrospective]] at the start of each cycle.
""",
    "Standing Desk": """---
tags: [health, equipment]
---

# Standing Desk

Alternating sitting and standing every hour reduced back pain. #health
""",
    "Intermittent Fasting": """---
tags: [nutrition]
date: 2025-03-01
---

# Intermittent Fasting

Trying the 16:8 protocol. Energy levels dip on day two of fasting, then
stabilise once the eating window is consistent.
""",
}


def write_sample_vault(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for name, text in SAMPLE_VAULT_NOTES.items():
        (root / f"{name}.md").write_text(text, encoding="utf-8")
    return root


@pytest.fixture
def sample_vault(tmp_path: Path) -> Path:
    return write_sample_vault(tmp_path / "vault")