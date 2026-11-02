"""
generation/synthesize.py — the only place in the system that produces
final answer prose from evidence.

Takes already-fused, already-ranked Evidence (from fusion/merge.py) and
makes one LLM call to produce an answer where each claim is tagged with
its supporting source_id/uri, per the "synthesis with provenance" design.

NOTE: like planner/analyzer.py, this calls an LLM client and has not been
exercised against a real OpenRouter API call in this environment. Fully
tested here with a fake client; needs a manual smoke test with a real
OPENROUTER_API_KEY before relying on it in a demo.
"""

from __future__ import annotations

from pathlib import Path

from capretrieve.contracts.result import Evidence
from capretrieve.llm.structured import CompletesText

PROMPT_PATH = Path(__file__).parent / "prompts" / "synthesis.md"

NO_EVIDENCE_ANSWER = "No permitted source returned evidence for this query."


def load_prompt_template() -> str:
    return PROMPT_PATH.read_text()


def _format_evidence_block(evidence: list[Evidence]) -> str:
    if not evidence:
        return "(no evidence was retrieved)"

    lines = []
    for i, item in enumerate(evidence, start=1):
        uri = item.uri if item.uri is not None else "(no uri)"
        lines.append(f"[{i}] source_id={item.source_id} uri={uri}\n{item.content}")
    return "\n\n".join(lines)


def synthesize(client: CompletesText, query: str, evidence: list[Evidence]) -> str:
    """
    Produce a final answer to `query` grounded in `evidence`, with inline
    [source_id: uri] citations per claim.

    `client` is injected (same dependency-injection pattern used
    throughout this project) so this is testable with a fake client
    returning canned prose, without a real OpenRouter call.

    With no evidence there is nothing to ground an answer in, so no LLM
    call is made. That also keeps a privacy-blocked query (empty plan) from
    being sent to the external LLM provider just to say "I don't know".
    """
    if not evidence:
        return NO_EVIDENCE_ANSWER

    template = load_prompt_template()
    prompt = template.replace("{query}", query).replace(
        "{evidence_block}", _format_evidence_block(evidence)
    )

    messages = [{"role": "user", "content": prompt}]
    return client.complete(messages)