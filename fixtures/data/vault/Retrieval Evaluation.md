---
tags: [evaluation, retrieval, metrics, thesis]
date: 2025-04-20
---

# Retrieval Evaluation

How to tell whether retrieval is actually good, instead of eyeballing three queries and declaring victory. This feeds straight into the evaluation chapter I'll need for [[Thesis Ideas]]. #evaluation

## First principle: evaluate retrieval separately from generation

In [[RAG Systems]] there are two places things go wrong: the retriever didn't find the right stuff, or the generator messed up with the right stuff in hand. End-to-end answer quality mixes them together. I want separate numbers:

- **Retrieval metrics**: did the relevant documents show up, and how high?
- **Generation metrics**: is the answer correct, faithful to the context, and complete?

This note is mostly about the first.

## Building a test set

The boring, essential part.

- Write 50 to 100 realistic queries. Mix of easy lookups, paraphrases, multi-hop, and questions with no answer in any source.
- For each query, label the relevant documents or chunks. Ideally graded: 2 = directly answers, 1 = partially useful, 0 = irrelevant.
- Label at document level first; chunk-level labels break every time I change the chunker.
- Keep a held-out split so I don't overfit my pipeline to my own test queries. I *will* be tempted.
- LLM-generated queries are a cheap way to bulk up, but they tend to reuse the document's wording, which flatters keyword search. Mark them separately.

## The metrics

### Recall@k

Fraction of relevant items that appear in the top k.

- recall@10 = (relevant in top 10) / (total relevant)
- My most important retriever metric, because in RAG the generator can only use what's retrieved. If it's not in the top k, it's gone.
- Doesn't care about order within the top k.

### Precision@k

Fraction of the top k that are relevant. Matters more than people think in RAG, since irrelevant chunks distract the model and cost tokens.

### MRR (Mean Reciprocal Rank)

For each query, take 1 / rank of the first relevant result, then average.

- First relevant at rank 1 gives 1.0, rank 2 gives 0.5, rank 10 gives 0.1.
- Good for "is there one right answer and how fast do we hit it" scenarios.
- Ignores everything after the first hit. Bad for queries needing several documents.

### nDCG@k

Normalised discounted cumulative gain.

- Each result contributes its graded relevance, discounted by log2(rank + 1).
- Normalise by the ideal ordering so scores land between 0 and 1.
- Uses graded labels and rewards putting the best documents first.
- My pick for comparing rankers and fusion strategies. Slightly harder to explain to non-IR people.

### Others to keep in mind

- **Hit rate@k**: was *anything* relevant in the top k? Crude, but easy to communicate.
- **Latency p50/p95**: a retriever that's 2% better and 4x slower is not better for an interactive tool.

#metrics

## How to judge a router

This is the part with less established practice, and therefore the interesting part. A router decides which source(s) to query (vault, local docs, web) before retrieval happens. I think it needs evaluating on several axes:

1. **Routing accuracy**: label each query with the correct source set. Measure exact match, plus per-source precision and recall. Treat it as multi-label classification.
2. **Downstream retrieval quality**: recall@k and nDCG@k of the final fused results compared to baselines:
   - query every source always (upper bound on recall, worst on cost),
   - single best source only,
   - an oracle router using gold labels (upper bound for routing).
3. **Cost**: number of sources queried per query, tokens, API calls, latency.
4. **Privacy leakage**: how often a query that should stay local gets sent to a web search API. Arguably this should be a hard constraint, not a metric, but I want to count violations.
5. **Freshness correctness**: for time-sensitive queries, did the router include a source that actually has current information?
6. **Abstention**: for unanswerable queries, does the system say so?

A useful framing: routing quality = how close we get to the oracle's retrieval scores while spending far less than query-everything.

## Pitfalls I want to avoid

- Reporting only averages. Break results down by query type; routers often fail on one category specifically.
- Tiny test sets with big claims. With 50 queries, a difference of 0.02 in nDCG is noise. Bootstrap confidence intervals or a paired test.
- Labelling with the system's own outputs (pooling bias). Unretrieved relevant documents never get labelled.
- Using an LLM as judge without checking it against my own labels on a sample first.

## Open questions

- How do I label "correct source" when two sources both contain the answer? Accept either? Require both?
- Should cost and quality be combined into one score, or presented as a Pareto plot? Leaning towards the plot.
- Is there a sensible way to evaluate freshness without constantly re-labelling?

## TODO

- [ ] Write the first 40 labelled queries, at least 10 that should never leave the machine.
- [ ] Implement recall@k, MRR and nDCG in a small script with unit tests on hand-computed examples.
- [ ] Set up the three baselines before touching the router.
