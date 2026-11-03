---
tags: [llm, ml, retrieval]
date: 2025-02-22
---

# Large Language Models

Notes on large language models from the angle I actually care about: how they interact with retrieval, how much context they can really use, and which tradeoffs matter when I'm running things on a laptop with a limited budget. #llm

## What they are (short version)

A large language model is a next-token predictor trained on a huge text corpus. Under the hood it's a stack of transformer blocks, and the part that makes it work is attention (my notes on that: [[Transformer Attention]]). After pretraining, most usable models go through instruction tuning and some kind of preference tuning so they follow instructions instead of just continuing text.

The thing I keep reminding myself: the model doesn't "look things up". Whatever it knows is compressed into the weights, lossy and frozen at the training cutoff.

## Parametric vs. retrieved knowledge

This is the core tension for my work.

- **Parametric knowledge** lives in the weights. Fast, no infrastructure, but stale, unverifiable, and fuzzy on rare facts. Ask a model about a niche library version and it'll make something up with total confidence.
- **Retrieved knowledge** comes in through the prompt. Fresh, citable, can include private data the model never saw. But it depends on the retriever finding the right thing, and it costs tokens.

That's why I'm interested in [[RAG Systems]]: let the model do what it's good at (reading, reasoning, writing) and let retrieval handle the facts. Open question for me: how do you tell when the model's prior should override a retrieved passage that's obviously wrong?

## Context windows

Context windows have grown dramatically: from a few thousand tokens to hundreds of thousands, and some models now advertise a million. Some people say this makes retrieval obsolete. I don't buy it.

Why long context doesn't replace retrieval (for me):

- **Cost**: every token in the prompt is billed or computed. Stuffing my whole vault into every query is absurd.
- **Latency**: time to first token grows with prompt length. Fine for batch jobs, annoying for interactive search.
- **Attention dilution**: models do worse at using information buried in the middle of a long prompt. Benchmarks that hide a single needle in a haystack are much easier than real questions that need several pieces combined.
- **Privacy**: if the model is a hosted API, everything in the context leaves my machine. Retrieval lets me send only the three relevant chunks.
- **Freshness**: the window doesn't help if the data isn't there. Something has to fetch it.

Where long context *does* help: fewer, larger chunks, less aggressive truncation, and multi-document reasoning once retrieval has narrowed things down.

## Tradeoffs I keep running into

| Choice | Upside | Downside |
|---|---|---|
| Big hosted model | Best quality, long context | Cost, data leaves machine, rate limits |
| Small local model | Private, free after setup, offline | Weaker reasoning, short context, slow on CPU |
| More retrieved chunks | Higher recall | Noise, cost, distraction |
| Fewer chunks | Focused answers | Missed facts |
| Temperature 0 | Reproducible | Can get stuck on bad phrasing |

For classification-style tasks like "which source should handle this query", a small model at temperature 0 with structured output is usually good enough. For final answer synthesis I still lean on a bigger one.

## Things models are bad at (that bite RAG)

- Admitting the context doesn't contain the answer.
- Counting, exact arithmetic, dates ("how many weeks since...").
- Respecting negations in the prompt ("don't use outside knowledge" is followed maybe 80% of the time).
- Keeping citations honest: sometimes they cite chunk 3 for a fact that came from chunk 5, or from nowhere.
- Consistency between runs, even at low temperature with hosted APIs.

## Open questions

- Is there a reliable way to get calibrated confidence out of a model? Token log-probs are a hint but not well calibrated after preference tuning.
- How much does the order of retrieved chunks matter? My hunch: put the best chunk first *and* last.
- At what model size does "route this query" become reliable? Could a tiny model do it with a few examples in the prompt?
- Do instruction-tuned models over-trust retrieved context, even when it's adversarial or wrong?

#retrieval

## TODO

- [ ] Benchmark a small local model vs. a hosted one on my routing prompts (accuracy and latency).
- [ ] Measure lost-in-the-middle on my own data with 5, 10 and 20 chunks.
- [ ] Read up on speculative decoding, mostly out of curiosity.
- [ ] Note token costs per query so I stop guessing.
