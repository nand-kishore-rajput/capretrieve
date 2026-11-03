---
tags: [vector-search, embeddings, infrastructure]
date: 2025-03-02
---

# Vector Databases

Everything I've learned (often the hard way) about storing embeddings and searching them quickly. This is the storage layer under my [[RAG Systems]] experiments. #embeddings

## Dense embeddings, briefly

An embedding model maps a piece of text to a fixed-length vector, typically 384, 768 or 1024 floats. Texts with similar meaning end up close together, usually measured with cosine similarity or dot product. "How do I fix my back" and "lower back pain exercises" should land near each other even though they share almost no words. That's the big win over keyword search.

Things that tripped me up:

- **Normalisation**: if vectors are normalised to unit length, cosine and dot product give the same ranking. If not, dot product favours long vectors. Check what the model expects.
- **Query vs. document prefixes**: some embedding models want "query: " and "passage: " prefixes. Forgetting them silently costs a few points of recall.
- **Model lock-in**: vectors from different models are not comparable. Switching models means re-embedding everything.
- **Domain mismatch**: general-purpose embeddings struggle with my shorthand notes, internal acronyms and code. Hybrid with BM25 papers over this.

## Exact vs. approximate search

Brute-force (flat) search compares the query against every vector. For my vault, a few thousand chunks, that's honestly fine and takes milliseconds. Approximate nearest neighbour (ANN) indexes only matter once you're into hundreds of thousands or millions of vectors, or when latency budgets are tight.

Opinion: people reach for ANN way too early. Flat search is exact, simple, and easy to debug.

## HNSW

Hierarchical Navigable Small World graphs. My mental model:

- Each vector is a node in a multi-layer graph.
- Top layers are sparse with long-range links; bottom layer has everyone with short-range links.
- Search starts at the top, greedily walks towards the query, drops a layer, repeats.

Knobs:

- `M`: number of neighbours per node. Higher means better recall and more memory.
- `ef_construction`: how hard to search when building. Higher means better graph, slower build.
- `ef_search`: how wide the search is at query time. The main recall vs. latency dial.

Pros: excellent recall/latency tradeoff, supports incremental inserts. Cons: memory hungry (the graph lives in RAM), deletes are awkward, and builds can be slow.

## IVF

Inverted file index. Cluster vectors with k-means into `nlist` buckets; at query time only search the `nprobe` closest buckets.

- Cheaper on memory than HNSW, especially combined with product quantisation (IVF-PQ), which compresses vectors into short codes.
- Needs a training step on representative data. If your data drifts, clusters go stale.
- Recall drops when the true neighbour sits just across a cluster boundary. Raising `nprobe` fixes that at the cost of speed.

Rule of thumb I've settled on: HNSW when it fits in memory, IVF-PQ when it doesn't.

## Chroma vs. alternatives

What I tried for the side project:

- **Chroma**: my current pick. Embedded mode, runs in-process, persists to a local directory, metadata filtering built in, uses HNSW under the hood. Perfect for a local-first personal tool. Downsides: not built for huge scale, and the API has changed between versions, which broke my code once.
- **FAISS**: a library rather than a database. Blazing fast, every index type you can think of, but you manage persistence and metadata yourself. Great for experiments.
- **Qdrant**: proper server, good filtering, nice payload model. Feels like the right step up if I ever deploy this somewhere.
- **pgvector**: vectors inside Postgres. Appealing because you get joins and transactions for free. Would pick this at work where Postgres already exists.
- **Managed cloud services**: no thanks for personal data. Private notes leaving my laptop defeats the purpose.

#vector-search

## Things to remember

- Store the raw text and metadata next to the vector, not just an id. Debugging is miserable otherwise.
- Keep a stable chunk id (hash of path and offset) so re-indexing is idempotent.
- Metadata filters before vector search (pre-filtering) can wreck HNSW recall if the filter is very selective. Check how the engine handles it.
- Similarity scores are not probabilities. Don't threshold at 0.8 and call it a day.

## Open questions

- Is it worth running a separate collection per source (vault, docs, web cache) or one collection with a source field? Separate feels cleaner for routing.
- How much recall do I actually lose with HNSW defaults vs. flat search on my data? Need to measure, not assume.
- Would a sparse learned representation beat BM25 for the keyword half of hybrid search?

## TODO

- [ ] Script a recall comparison: flat vs. HNSW at three `ef_search` values.
- [ ] Pin the Chroma version in requirements.
- [ ] Try one smaller embedding model to see if latency drops without hurting recall.
