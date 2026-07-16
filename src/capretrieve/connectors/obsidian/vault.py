"""
Vault loading — wraps LlamaIndex's ObsidianReader and layers on the parsing
it doesn't do itself: YAML frontmatter and inline #tags.

ObsidianReader (llama_index.readers.obsidian) already walks the vault and
extracts wikilinks + backlinks per note; we reuse that rather than
re-implementing wikilink parsing (reuse-over-reinvention). Frontmatter and
tags are NOT extracted by the upstream reader — its underlying
MarkdownReader treats a frontmatter block as ordinary body text — so this
module re-reads each file directly for those two things and merges the
result onto what ObsidianReader already produced.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from llama_index.readers.obsidian import ObsidianReader
from pydantic import BaseModel

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?\n)---\s*\n?", re.DOTALL)
_INLINE_TAG_RE = re.compile(r"(?<!\S)#([A-Za-z0-9_/-]+)")


class Note(BaseModel):
    """A single parsed vault note, ready for keyword lookup or graph
    traversal. Produced by load_vault() — not constructed directly
    elsewhere."""

    note_name: str
    file_name: str
    folder_name: str
    path: str
    frontmatter: dict
    tags: list[str]
    wikilinks: list[str]
    backlinks: list[str]
    content: str


def _parse_frontmatter(raw_text: str) -> tuple[dict, str]:
    """Split a note's raw text into (frontmatter dict, remaining body).

    Returns ({}, raw_text) if there's no frontmatter block, or if the block
    fails to parse as YAML / isn't a mapping. A malformed frontmatter block
    is treated as absent rather than fatal — one bad note shouldn't take
    down the whole vault load.
    """
    match = _FRONTMATTER_RE.match(raw_text)
    if not match:
        return {}, raw_text

    body = raw_text[match.end():]
    try:
        parsed = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}, raw_text

    if not isinstance(parsed, dict):
        return {}, raw_text

    return parsed, body


def _extract_inline_tags(text: str) -> list[str]:
    """Obsidian inline tags: #tag or #nested/tag, anywhere in the body."""
    return sorted(set(_INLINE_TAG_RE.findall(text)))


def _normalize_frontmatter_tags(frontmatter: dict) -> list[str]:
    """Frontmatter tags can be a YAML list or a single string; normalize
    to a list either way."""
    raw = frontmatter.get("tags")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(t) for t in raw]
    return []


def load_vault(vault_dir: Path) -> dict[str, Note]:
    """
    Load every markdown note in vault_dir into a dict keyed by note_name.

    Wikilinks/backlinks come from ObsidianReader's metadata. Frontmatter
    and tags are parsed here directly from each file, since ObsidianReader
    doesn't extract either.
    """
    reader = ObsidianReader(input_dir=str(vault_dir))
    documents = reader.load_data()

    notes: dict[str, Note] = {}
    for doc in documents:
        meta = doc.metadata
        note_name = meta["note_name"]
        file_path = Path(meta["folder_path"]) / meta["file_name"]

        raw_text = file_path.read_text(encoding="utf-8")
        frontmatter, body = _parse_frontmatter(raw_text)

        tags = sorted(
            set(_normalize_frontmatter_tags(frontmatter))
            | set(_extract_inline_tags(body))
        )

        notes[note_name] = Note(
            note_name=note_name,
            file_name=meta["file_name"],
            folder_name=meta["folder_name"],
            path=str(file_path),
            frontmatter=frontmatter,
            tags=tags,
            wikilinks=list(meta.get("wikilinks", [])),
            backlinks=list(meta.get("backlinks", [])),
            content=body.strip(),
        )

    return notes