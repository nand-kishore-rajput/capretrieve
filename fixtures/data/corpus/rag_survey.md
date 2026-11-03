# Retrieval-Augmented Generation: A Survey

Retrieval-augmented generation (RAG) is a family of techniques that combine a parametric language model with a non-parametric external memory. Instead of relying only on knowledge stored in its weights during pre-training, a RAG system retrieves relevant passages from a document collection at inference time and conditions the language model's output on them. The approach addresses several weaknesses of standalone large language models (LLMs): knowledge that goes stale after the training cutoff, poor coverage of private or domain-specific material, and a tendency to produce fluent but unsupported statements. This survey describes the core architecture, the progression from naive to advanced pipelines, the main design choices around chunking and reranking, the evidence on hallucination reduction, and the problems that remain open.

## Core Architecture: Retriever and Generator

A RAG system has two principal components. The **retriever** maps a user query to a small set of candidate passages drawn from a corpus. The **generator** is a sequence-to-sequence or decoder-only language model that receives the query together with the retrieved passages and produces the final answer.

Retrievers fall into three broad categories. Sparse retrievers such as BM25 score documents by weighted term overlap and need no training. Dense retrievers such as Dense Passage Retrieval (DPR) encode queries and passages into a shared vector space with neural encoders and rank by inner product or cosine similarity. Hybrid retrievers run both and merge their result lists, often with Reciprocal Rank Fusion (RRF). Dense retrieval is usually served from an approximate nearest neighbour index such as HNSW or IVF so that latency stays low on corpora of millions of passages.

The generator can consume the evidence in different ways. The most common method today is in-context augmentation: the retrieved passages are concatenated into the prompt, usually with instructions to answer only from the supplied context and to cite sources. Earlier research models trained the retriever and generator jointly, marginalizing over retrieved documents during training so that retrieval quality improved in response to the generation loss. Fusion-in-decoder architectures encode each passage separately and let the decoder attend over all encoded passages at once, which scales better to many passages than plain concatenation.

## Naive RAG

The simplest pipeline, often called naive RAG, follows an index-retrieve-generate pattern. Documents are split into fixed-size chunks, each chunk is embedded and stored in a vector database, the query is embedded with the same model, the top-k most similar chunks are retrieved, and these chunks are placed into a prompt for the LLM.

Naive RAG is easy to build and often gives a large improvement over a model with no retrieval. Its weaknesses are well known, however. Retrieval precision can be low, so irrelevant chunks dilute the context. Recall can be low when the query wording differs from the document wording. Fixed-size chunks may split a key fact across a boundary. The generator may ignore the context, over-trust a misleading passage, or struggle when the relevant information sits in the middle of a long prompt, a behaviour sometimes described as "lost in the middle."

## Advanced RAG

Advanced RAG adds processing stages before and after retrieval to address these failures.

**Pre-retrieval** techniques work on the query or the index. Query rewriting uses an LLM to reformulate an ambiguous or conversational question into a standalone search query. Query expansion adds synonyms or generates several paraphrases and retrieves for each. Hypothetical document embedding generates a plausible answer first and uses its embedding as the search vector, on the idea that answers resemble other answers more than questions do. On the index side, metadata such as dates, authors or document type can be attached to chunks to support filtering.

**Post-retrieval** techniques work on the candidate set. Reranking reorders candidates with a stronger model. Context compression removes sentences that are irrelevant to the query so that more useful evidence fits in the context window. Deduplication removes near-identical chunks that waste tokens.

**Iterative and adaptive** retrieval goes beyond a single retrieval step. The system may retrieve, generate a partial answer, then retrieve again based on what is still missing. Some systems let the model decide whether retrieval is needed at all, skipping it for questions the model can answer reliably from parametric knowledge. Multi-hop questions, which need facts from several documents that must be chained together, benefit especially from iterative designs.

Modular RAG generalizes these ideas, treating routing, search, memory, fusion and generation as interchangeable modules that can be arranged differently for different tasks or sources.

## Chunking Strategies

How documents are segmented has a large effect on retrieval quality. Fixed-length chunking splits text every N tokens, often with an overlap of 10 to 20 percent so that facts near a boundary appear in two chunks. Structure-aware chunking follows natural boundaries such as paragraphs, Markdown headings, or code functions. Semantic chunking places breaks where the embedding similarity between adjacent sentences drops, aiming to keep each chunk on a single topic.

Chunk size involves a tradeoff. Small chunks give precise embeddings and let more distinct pieces of evidence fit into the prompt, but they may lack the surrounding context needed to interpret them. Large chunks keep context but produce blurred embeddings that represent several topics at once. Hierarchical approaches index small chunks for matching but return the larger parent section to the generator, getting some of the benefit of both.

## Reranking

First-stage retrievers are built for speed, so they score the query and the document independently. A reranker is a slower, more accurate model applied to the top few dozen or few hundred candidates. The most common design is a cross-encoder: a transformer such as BERT that takes the query and a candidate passage concatenated together and outputs a relevance score. Because every query token can attend to every document token, cross-encoders capture fine-grained interactions that bi-encoders miss. Late-interaction models such as ColBERT sit between the two, keeping per-token embeddings and computing a cheap token-level similarity. LLM-based rerankers prompt a language model to score or sort candidates, either one at a time or as a list.

Reranking usually gives substantial gains in precision at small k, which matters because only a handful of passages fit comfortably in the generator's context.

## How RAG Reduces Hallucination

Hallucination is the generation of content that is not supported by the input or by real-world facts. RAG reduces it in several ways. Grounding the model in retrieved text gives it access to facts it may never have learned or may have learned imperfectly. Instructions to answer only from the context and to say when the context is insufficient encourage the model to abstain rather than guess. Citations make answers verifiable, so users and automated checkers can confirm each claim against its source.

RAG does not remove hallucination entirely. If retrieval returns irrelevant or wrong passages, the model may confidently repeat the errors. The model may also blend retrieved facts with parametric knowledge in unsupported ways, or misread a passage. Faithfulness evaluation, which checks whether each claim in the answer is entailed by the retrieved context, is therefore a standard part of RAG quality assessment.

## Open Challenges

Several problems remain active research areas. **Retrieval quality** on complex, multi-hop or ambiguous queries is still limited. **Context utilization** is imperfect: models do not always use the most relevant passage, and performance can drop as more passages are added. **Conflicting evidence** between sources, or between sources and the model's parametric knowledge, has no generally accepted resolution strategy. **Evaluation** is difficult because it must judge both retrieval and generation, and automated judges introduce their own biases. **Efficiency** matters because retrieval, reranking and long prompts all add latency and cost. **Security and privacy** concerns include prompt injection through retrieved documents and leakage of sensitive content to users who should not see it. Finally, **source selection** across heterogeneous back ends, such as vector stores, knowledge graphs, web search and private databases, raises routing questions about capability, freshness and access control.

## Summary

Retrieval-augmented generation pairs a retriever with a language model so that answers are grounded in external, updatable knowledge. Naive pipelines that embed chunks and retrieve the top-k are a useful starting point, while advanced pipelines add query rewriting, hybrid search, reranking, compression and iterative retrieval. Chunking and reranking choices strongly influence quality. RAG reduces but does not eliminate hallucination, and open challenges remain in retrieval for complex queries, context use, conflict resolution, evaluation, efficiency and security.
