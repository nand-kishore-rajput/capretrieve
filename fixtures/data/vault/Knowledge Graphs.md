---
tags: [knowledge-graphs, obsidian, retrieval]
date: 2025-04-06
---

# Knowledge Graphs

I started this note because my vault *is* a graph and I've been ignoring that while building a purely vector-based retriever. Collecting thoughts on whether graph structure should play a role, possibly as part of [[Thesis Ideas]]. #knowledge-graphs

## What I mean by "knowledge graph"

Two quite different things get called a knowledge graph, and I keep mixing them up:

1. **Formal KGs**: entities and typed relations as triples, like (Berlin, capital_of, Germany). Schemas, ontologies, query languages like SPARQL or Cypher. Precise but expensive to build and maintain.
2. **Loose document graphs**: nodes are documents or notes, edges are links, backlinks, shared tags or co-citation. No schema, relations are untyped. That's what Obsidian gives me for free.

For a personal tool, option 2 is the realistic one. Nobody hand-curates triples about their own life. Well, almost nobody.

## Graph traversal vs. semantic search

How they differ, as far as I can tell:

**Semantic (vector) search**
- Finds things that *sound like* the query.
- Great for fuzzy, paraphrased questions.
- Blind to structure: doesn't know that note A explicitly references note B.
- Each result is judged in isolation.

**Graph traversal**
- Starts from one or more seed nodes and follows edges.
- Great for "what's connected to X", multi-hop questions and context expansion.
- Only as good as the edges. Missing links mean missing results.
- Needs an entry point, which usually comes from... search.

So the obvious combo: use semantic search to find seed nodes, then expand one or two hops along links to pull in related context. Basically "GraphRAG-lite".

Example from my own vault: if I ask "what did I decide about chunking?", vector search finds the note where I wrote about chunk sizes. But the actual decision is in a linked note about a test run that never uses the word "chunking" in a way the embedding picks up. One hop along the link would catch it.

## Obsidian as a graph

What Obsidian gives me structurally:

- **Wikilinks**: explicit, intentional edges. When I link something, I'm saying it matters for this note. That's a strong relevance signal, arguably stronger than embedding similarity.
- **Backlinks**: the reverse edges, computed automatically.
- **Tags**: both frontmatter tags and inline tags. They act like hyperedges grouping many notes.
- **Folders**: weak signal, mostly organisational.
- **Unresolved links**: links to notes that don't exist yet, which is kind of a to-do list of concepts.

The graph view is pretty but honestly not that useful for finding things. The structure underneath is the useful part.

Things I've noticed about my own linking habits:

- Hub notes (like my study overview notes) have tons of links and would dominate any naive PageRank.
- I link generously when I'm fresh and lazily when tired, so link density varies by mood, not relevance.
- Some important relationships are only in my head and never become links.

#obsidian

## Ideas for using the graph in retrieval

- **Link-based expansion**: after retrieving top k chunks, add the notes they link to, with decaying weight per hop.
- **Graph-aware reranking**: boost results that are linked from or to other top results. Mutual links suggest a coherent cluster.
- **Personalised PageRank** seeded from the query's top hits, as a second scoring signal to fuse with vector scores.
- **Tag filters**: if the query mentions a topic matching a tag, restrict or boost.
- **Routing signal**: if the query mentions a note title verbatim, that's a strong hint the vault is the right source.

## Problems I foresee

- Hub notes will pollute expansion. Need degree normalisation.
- Two-hop expansion explodes fast. Need a hard budget on how many notes get added.
- Evaluation gets harder: is an expanded note relevant or just nearby? Need labels.
- Graph edges in other sources (local PDFs, web pages) are either missing or totally different in nature, so this only helps one source. That asymmetry is interesting for a router: some sources support structural retrieval and some don't.

## Open questions

- Does link expansion actually improve recall on my vault, or does it just add noise? I genuinely don't know.
- Should edges be weighted by where the link appears (heading vs. footnote)?
- Is it worth extracting typed relations with an LLM, or is that overkill for a personal vault?
- Could "paradigm" (graph traversal vs. semantic vs. keyword) be one of the capabilities a router reasons about per source?

## TODO

- [ ] Parse wikilinks from all notes into an adjacency list.
- [ ] Compute degree distribution to find hub notes.
- [ ] Prototype one-hop expansion and compare recall@10 with and without it.
- [ ] Write down five multi-hop questions about my vault to use as test cases.
