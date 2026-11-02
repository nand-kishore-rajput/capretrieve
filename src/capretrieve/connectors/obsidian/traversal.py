"""
Link-neighbourhood expansion — the graph_traversal retrieval mode.

Given a seed note, walks outward via wikilinks and backlinks up to a
bounded depth, returning every note reached. This is what backs
paradigm=graph_traversal queries — e.g. S4: "what other notes link to my
project retrospective, and what did those say?"
"""

from __future__ import annotations

from capretrieve.connectors.obsidian.vault import Note


def expand_neighbourhood(
    notes: dict[str, Note], seed: str, depth: int = 1
) -> list[Note]:
    """
    Return the seed note plus every note reachable within `depth` hops via
    either wikilinks (outgoing) or backlinks (incoming).

    depth=0 returns just the seed note, if it exists. Unknown seed
    note_names return an empty list rather than raising — the caller
    (connector.py) decides how to report "not found".

    Results are in breadth-first order: the seed first, then each hop's
    notes sorted by name. The connector truncates to top_k, so this order
    decides what survives — the seed must never be the note that's cut.
    """
    if seed not in notes:
        return []

    visited: set[str] = {seed}
    ordered: list[str] = [seed]
    frontier: set[str] = {seed}

    for _ in range(depth):
        next_frontier: set[str] = set()
        for note_name in frontier:
            note = notes.get(note_name)
            if note is None:
                continue
            neighbours = set(note.wikilinks) | set(note.backlinks)
            next_frontier |= neighbours - visited
        visited |= next_frontier
        ordered.extend(sorted(next_frontier))
        frontier = next_frontier
        if not frontier:
            break

    return [notes[name] for name in ordered if name in notes]