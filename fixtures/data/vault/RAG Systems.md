---
tags: [rag, retrieval, llm, thesis]
date: 2025-03-14
---

# RAG Systems

My working notes on retrieval-augmented generation. I keep coming back to this page whenever something breaks in my side project, so it's half explainer, half bug diary. #rag

## The basic idea, in my words

RAG systems glue a retriever onto a generator. The user asks something, the retriever fetches a handful of passages that look relevant, and those passages get pasted into the prompt of a model (see [[Large Language Models]]) together with the question. The model then answers "grounded" in that context instead of purely from whatever it memorised during training.

That's the whole trick. Everything interesting is in the details of how retrieval is done and what you do when it goes wrong.

## A typical retrieval pipeline

What I've actually built, roughly in order:

1. **Ingestion**: load documents (markdown notes, PDFs, HTML), strip boilerplate, keep metadata like title, path and date.
2. **Chunking**: split into pieces of about 300 to 800 tokens. I use heading-aware splitting for markdown because splitting mid-section destroys meaning.
3. **Embedding**: run each chunk through an embedding model and store the vector plus metadata in a vector store (notes in [[Vector Databases]]).
4. **Query processing**: optionally rewrite the user query, expand acronyms, or split a multi-part question into sub-queries.
5. **Retrieval**: dense search, keyword search (BM25), or both. Hybrid wins in almost every test I've run.
6. **Fusion and reranking**: merge result lists (reciprocal rank fusion is my default) and optionally rerank the top 50 with a cross-encoder.
7. **Context assembly**: pick the top k chunks, dedupe, order them, and fit them into the token budget.
8. **Generation**: prompt the model with instructions like "answer only from the context, say if you don't know, cite chunk ids".

Opinion: steps 2 and 6 matter way more than which embedding model you pick. People argue about embedding leaderboards while their chunker is cutting tables in half.

## Why retrieval reduces hallucination (and when it doesn't)

The argument goes like this: a model hallucinates when it has to produce a specific fact it doesn't reliably know. If the fact is sitting right there in the context, the model mostly copies it. So retrieval turns a recall problem into a reading comprehension problem, and models are much better at reading than remembering.

But this only holds if:

- the right passage was actually retrieved (recall),
- it's not drowned out by ten irrelevant passages (precision),
- the prompt tells the model to prefer the context over its priors,
- the model is willing to say "not in the context".

When any of these fail, you get a *confident* wrong answer that now also comes with a citation, which is arguably worse than a plain hallucination.

## Failure modes I've personally hit

- **Missed retrieval**: the answer exists but the query wording doesn't match. Classic with my own notes, because I write in shorthand. Hybrid search helps here.
- **Wrong source entirely**: a question about my private notes gets answered from the web corpus. This is basically the routing problem I want to study.
- **Stale context**: the corpus has an old version of a fact and a newer one, and the retriever happens to prefer the old one.
- **Chunk boundary loss**: the key sentence is in chunk 12 but its subject is introduced in chunk 11.
- **Lost in the middle**: with long contexts, stuff in the middle of the prompt gets ignored more than stuff at the start or end.
- **Over-retrieval**: top_k = 20 "just to be safe" made answers worse, not better. More noise, more distraction.
- **Score miscalibration**: cosine similarity of 0.78 means nothing in absolute terms and differs across embedding models, so thresholds don't transfer.

## Design questions I haven't settled

- Should the system ever decide *not* to retrieve? For "what is 2+2" retrieval is pure overhead. Adaptive retrieval sounds nice but adds another model call.
- How to handle multiple heterogeneous sources (my vault, local docs, web) without just querying everything every time? Querying everything is slow, leaks private queries to web APIs, and floods the context.
- Is reranking worth the latency for a personal tool? On my laptop a cross-encoder adds roughly 300 ms for 50 candidates.
- Where does freshness fit in? Web results are fresh but noisy; my notes are trusted but sometimes outdated.

## How I want to measure it

Gut feeling is not evaluation. I need a small labelled set of queries with known relevant chunks, and then recall@k for the retriever and a separate faithfulness check for answers. Details are in [[Retrieval Evaluation]].

#retrieval

## TODO

- [ ] Try parent-document retrieval: embed small chunks, return the surrounding section.
- [ ] Log every query with the chunks retrieved so I can debug misses later.
- [ ] Compare RRF constant k = 60 against k = 10 on my vault queries.
- [ ] Write a "refuse if context empty" guard and test how often it triggers.
- [ ] Figure out whether query rewriting helps or just adds latency.
