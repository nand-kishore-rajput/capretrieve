"""
Keyword baseline: TF-IDF cosine similarity between the query and each
connector's free-text `scope` string. No LLM, fully deterministic.

This is the "route by description text" approach with the intelligence
removed: it sees exactly what a tool-calling LLM sees (names + prose) but
matches words instead of reasoning. It reads `scope`, which the planner is
forbidden to read. That contrast is the point of the baseline.

Selection uses the SAME relative-threshold rule as the CapRetrieve planner
(every connector within RELATIVE_THRESHOLD of the top score), so any
difference in the results comes from the matching signal, not from a
different selection policy. If no connector shares a single term with the
query, the plan is empty.

Pure Python on purpose: no scikit-learn dependency for ~40 lines of maths.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from collections.abc import Sequence
from typing import Any

from capretrieve.evaluation.records import RouteDecision

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Small fixed list: with ~3 short scope strings, function words would
# otherwise dominate the overlap.
STOPWORDS = frozenset(
    """a an and are as at be by can could did do does for from has have how i
    if in into is it its me my of on or our should so than that the their them
    there these this those to was we were what when where which who why will
    with you your""".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


class TfIdfIndex:
    def __init__(self, docs: dict[str, str]) -> None:
        tokenized = {doc_id: tokenize(text) for doc_id, text in docs.items()}
        n = len(tokenized)
        df = Counter(term for toks in tokenized.values() for term in set(toks))
        # smoothed idf (same form as scikit-learn's default)
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}
        self.vectors = {doc_id: self._vector(toks) for doc_id, toks in tokenized.items()}

    def _vector(self, tokens: list[str]) -> dict[str, float]:
        tf = Counter(t for t in tokens if t in self.idf)
        vec = {t: c * self.idf[t] for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values()))
        return {t: v / norm for t, v in vec.items()} if norm else {}

    def scores(self, query: str) -> dict[str, float]:
        q = self._vector(tokenize(query))
        return {
            doc_id: sum(w * vec.get(t, 0.0) for t, w in q.items())
            for doc_id, vec in self.vectors.items()
        }


def select_relative(scores: dict[str, float], relative_threshold: float) -> list[str]:
    """Everything within `relative_threshold` of the top score, best first."""
    top = max(scores.values(), default=0.0)
    if top <= 0.0:
        return []
    cutoff = top * (1.0 - relative_threshold)
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [cid for cid, s in ranked if s >= cutoff]


class KeywordRouter:
    name = "keyword"
    deterministic = True
    model = None

    def __init__(self, manifests: Sequence[Any], relative_threshold: float) -> None:
        self._index = TfIdfIndex({m.connector_id: m.scope for m in manifests})
        self._relative_threshold = relative_threshold

    async def route(self, query: str) -> RouteDecision:
        scores = self._index.scores(query)
        return RouteDecision(
            selected=select_relative(scores, self._relative_threshold),
            raw_output=json.dumps({k: round(v, 4) for k, v in scores.items()}),
        )


def build_keyword_router() -> KeywordRouter:
    from capretrieve.manifest.loader import load_manifest_dir
    from capretrieve.planner.selection import RELATIVE_THRESHOLD
    from capretrieve.settings import get_settings

    manifests = list(load_manifest_dir(get_settings().config_dir).values())
    return KeywordRouter(manifests, relative_threshold=RELATIVE_THRESHOLD)