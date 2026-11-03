---
tags: [thesis, retrieval, research]
date: 2025-05-28
---

# Thesis Ideas

Running brainstorm for my master's thesis. Supervisor meeting is coming up and I need to walk in with one clear direction instead of five half-ideas. Current frontrunner below. #thesis

## Working title

**Capability-aware query routing across heterogeneous retrieval sources**

Alternative titles I've scribbled:
- "Ask the right source: routing queries by privacy, paradigm and freshness"
- "Not every question needs the web"

## The problem in one paragraph

Personal assistants increasingly search several sources at once: private notes, local documents, and the open web. The default is to query everything and merge, which is slow, wastes tokens, floods the context with noise, and can leak private queries to external services. Most routing work I've seen picks between sources based on topic or content similarity only. I think a router should reason about what each source can actually *do* (its capabilities) and what the query actually *needs*.

## The three capability dimensions

### 1. Privacy

- Each source has a privacy level: local and private (personal vault), local but shareable (downloaded papers, manuals), or external (web search API).
- Each query has a sensitivity level. "What did my doctor say about X" must never go to a web API, even if the web would give a decent generic answer.
- Hypothesis: treating privacy as a hard constraint, not a soft score, costs very little recall.

### 2. Paradigm

- Sources support different retrieval paradigms: semantic vector search, keyword/BM25, graph traversal over links (see [[Knowledge Graphs]]), live web search.
- Queries suit different paradigms: exact names and codes suit keyword, paraphrased questions suit semantic, "what's connected to X" suits graph.
- Router picks not just *which* source but *how* to query it.

### 3. Freshness

- Some sources are static snapshots, some are updated occasionally, the web is live.
- Queries have different time sensitivity: "latest version of X" vs. "what is attention".
- Router should send time-sensitive queries to fresh sources and flag when only stale sources are allowed (e.g. private plus time-sensitive).

## Research questions (draft)

1. **RQ1**: Does capability-aware routing match query-everything retrieval quality while querying fewer sources?
2. **RQ2**: How much does each dimension (privacy, paradigm, freshness) contribute? Ablation.
3. **RQ3**: How do rule-based, small-LLM and hybrid routers compare on accuracy, latency and privacy violations?
4. Maybe **RQ4**: Can the router explain its decisions in a way users find trustworthy? Might be out of scope.

## Method sketch

- Build a prototype router with source capability profiles (declared metadata per source) and a query analyser (small LLM with structured JSON output, plus some heuristics).
- Three sources: a synthetic personal vault, a local document corpus, and web search.
- Test set of labelled queries with gold sources and relevance judgments. Must include privacy-sensitive, time-sensitive, and unanswerable queries.
- Baselines: query-all, single best source, content-similarity router, oracle router.
- Metrics: routing accuracy, recall@k, nDCG@k, sources per query, latency, privacy violation count. Details in [[Retrieval Evaluation]].
- Log a routing trace per query so every decision can be inspected afterwards.

#research

## Risks and worries

- **Dataset**: no public benchmark fits this exactly. I'll need to build one, which is a lot of work and invites "you designed the test to fit the method" criticism. Mitigation: write queries before building the router, get a friend to write a share of them blind.
- **Synthetic vault**: using my real notes is impossible for privacy reasons (ironic). A synthetic persona vault is the way, but it must be realistic enough.
- **Web results change**: reproducibility is a problem. Cache web results at evaluation time and report the date.
- **Scope creep**: the graph paradigm alone could be a thesis. Keep it as one option among several, don't go deep.
- **"Just use a bigger model"**: reviewers may ask why not stuff everything into a long context. Need a cost and privacy argument with numbers.

## Other ideas (backup options)

- Evaluating chunking strategies on personal notes with heavy shorthand.
- Graph-aware reranking for linked note collections.
- Measuring how often LLMs override correct retrieved context with wrong prior knowledge.

None excite me as much as the routing topic, but good to have a fallback if the supervisor shoots it down.

## Reading to do

I've parked a pile of papers and books on query routing, federated search, adaptive retrieval and privacy-preserving search in [[Reading List]]. Need to get through the federated search ones first; that old IR literature probably solved half of this already, and I'd rather find out now than in the related work chapter.

## Questions for supervisor

- Is building my own benchmark acceptable as a contribution, or does it need to be secondary?
- Is a user study needed, or is offline evaluation enough for a master's thesis?
- How strict should the privacy model be: binary local/external, or graded?
- Can I use a hosted LLM for the router, or should everything run locally to be consistent with the privacy story?

## TODO

- [ ] Write a one-page proposal with title, problem, RQs and method.
- [ ] Draft capability profiles for the three sources as YAML.
- [ ] Draft 30 test queries before writing any router code.
- [ ] Book the supervisor meeting.
