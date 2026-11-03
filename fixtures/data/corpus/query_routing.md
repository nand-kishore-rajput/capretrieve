# Query Routing Across Heterogeneous Retrieval Sources

Many information systems draw on more than one source of knowledge: a vector index of internal documents, a full-text search engine, a knowledge graph, a relational database, a web search API, and perhaps a collection of personal or confidential records. Sending every query to every source is wasteful, slow and sometimes unsafe. **Query routing** is the process of deciding, for each incoming query, which sources to consult, how to query them, and how to combine their results. The problem has roots in federated search and distributed information retrieval, and it has become central to retrieval-augmented generation systems that must assemble context from diverse back ends. This article describes the main routing strategies and the factors that drive routing decisions: source capabilities, privacy constraints, freshness requirements, and cost and latency.

## Why Routing Matters

Retrieval sources differ along many dimensions. Some are strong at semantic matching of paraphrased questions, others at exact keyword or identifier lookups, and others at structured queries with filters and aggregation. Some contain current data, others are updated rarely. Some are free and fast, others charge per call or take seconds to respond. Some hold sensitive data that must never leave a controlled environment.

Querying all sources and merging everything has several drawbacks. It increases latency to that of the slowest source, multiplies cost, can exceed rate limits, and floods the downstream ranker or language model with irrelevant results, which can lower answer quality. It may also violate policy by sending a confidential query to an external service. Good routing improves relevance, efficiency and compliance at the same time.

## Routing Strategies

**Rule-based routing** uses explicit conditions: keywords, regular expressions, query length, the presence of identifiers, or the user's role. For example, a query that contains a ticket number is routed to the issue tracker. Rules are transparent and predictable but brittle and hard to maintain as sources multiply.

**Classifier-based routing** trains a model to predict the appropriate source or sources from the query text, framing routing as single-label or multi-label classification. Training data can come from logs of which sources produced clicked or cited results. Lightweight classifiers or embedding-similarity methods, which compare the query embedding with descriptions or sample queries for each source, add little latency.

**LLM-based routing** prompts a language model with descriptions of the available sources and asks it to select one or more, often through a function-calling or tool-use interface. This handles open-ended queries flexibly and can decompose a complex question into sub-queries for different sources, but it adds the latency and cost of a model call and can be inconsistent.

**Resource selection** methods from federated search estimate how many relevant documents each source is likely to hold, using sampled content, term statistics or the results of previous queries, and rank sources by that estimate.

**Cascading** and **adaptive** strategies query a cheap source first and escalate to more expensive sources only if the initial results are weak, measured by retrieval scores, the number of results, or a confidence estimate from the generator.

In practice, systems often combine these: hard rules enforce policy, a classifier or LLM proposes candidate sources, and scoring based on metadata picks the final set.

## Capability Metadata

Effective routing depends on accurate descriptions of what each source can do. **Capability metadata** is a structured profile attached to each source. Typical fields include:

- **Content domain**: the topics, document types or entity types covered.
- **Query modes**: whether the source supports semantic search, keyword search, structured filters, graph traversal, aggregation or exact identifier lookup.
- **Freshness**: how often the source is updated and the time range it covers.
- **Sensitivity and access**: the data classification and which users or roles may query it.
- **Location**: whether the source runs locally, inside a private network, or as an external third-party service.
- **Cost and performance**: typical latency, per-call cost and rate limits.
- **Result format**: passages, records, triples or summaries, which affects how results are merged.

Capability metadata turns routing into a matching problem between the requirements of a query and the profiles of the sources. It also makes routing decisions explainable, since the system can record which capability or constraint led to each source being included or excluded. Keeping metadata accurate as sources change is an ongoing operational task.

## Privacy and Access Constraints

Privacy constraints are usually treated as hard requirements rather than preferences to be traded off. Common patterns include:

- **Data residency**: queries that contain or concern sensitive information, such as health or personal data, may be restricted to local or on-premises sources and kept from external APIs.
- **Access control**: a user should only receive results from sources and documents they are authorized to see. Routing can exclude sources entirely, while document-level filtering enforces finer permissions inside a source.
- **Query sensitivity detection**: classifiers or pattern matchers identify personal identifiers or confidential terms in the query and tighten routing accordingly.
- **Minimization**: when an external source must be used, the query may be rewritten to remove identifying details.

A sound design applies policy filters before any relevance-based scoring, so that a highly relevant but disallowed source is never queried. Audit logs of routing decisions support compliance review.

## Freshness

Some questions depend on current information: prices, news, system status, recent tickets or schedules. Others concern stable knowledge for which an older reference corpus is ideal. Routing can estimate a query's **temporal sensitivity** from cues such as words like "latest", "today" or "current", explicit dates, or the topic category. Time-sensitive queries are routed to live or frequently updated sources, while stable queries can use cached or static indexes that are cheaper and often of higher quality.

Freshness also affects result merging. When sources disagree, a newer document may be preferred for time-sensitive facts. Index lag, the delay between a document changing and the index reflecting it, should be part of each source's metadata.

## Cost and Latency

Each source has a cost profile in money, compute and time. Local vector searches may return in milliseconds; web search or large-model reranking may take hundreds of milliseconds to seconds and incur per-call fees. Routers manage this budget in several ways:

- **Selective fan-out**: querying only the sources with high expected value.
- **Parallel execution with timeouts**: querying selected sources concurrently and proceeding with whatever has returned when a deadline passes.
- **Caching**: reusing results for repeated or similar queries.
- **Tiered escalation**: trying cheap sources first and adding expensive ones only when needed.

The router itself must be cheap relative to the retrieval it controls, which is why lightweight classifiers or rules are often placed in front of, or instead of, LLM-based routing.

## Merging Results

Once several sources return results, their scores are generally not comparable: a BM25 score, a cosine similarity and a graph match have different scales and meanings. Rank-based fusion methods such as Reciprocal Rank Fusion combine lists using only positions, while score-normalization methods rescale scores before combining. A reranker can then reorder the merged candidates. It is also common to cap the number of results per source so that no single source dominates the final context.

## Summary

Query routing selects which retrieval sources to consult for each query in a heterogeneous system. Strategies range from rules and classifiers to LLM-based selection and cascades. Capability metadata describing content, query modes, freshness, sensitivity, location and cost lets routing be treated as matching query requirements to source profiles. Privacy constraints act as hard filters applied before relevance scoring, freshness requirements steer time-sensitive queries toward live sources, and cost and latency budgets limit fan-out. Results from the selected sources are then merged with fusion and reranking.
