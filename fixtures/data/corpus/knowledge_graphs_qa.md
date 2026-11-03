# Knowledge Graphs for Question Answering

A knowledge graph (KG) is a structured representation of facts as a network of entities connected by typed relations. Knowledge graphs underpin search engine knowledge panels, enterprise data integration, biomedical research databases and many question-answering systems. Compared with unstructured text, a graph makes relationships explicit, which allows precise lookups, chained reasoning across several facts, and answers that can be traced back to specific edges. This article explains how knowledge graphs are represented, how question answering over them works, how multi-hop traversal supports complex questions, and how graph-based retrieval compares with and complements semantic retrieval over text.

## Representation

The basic unit of a knowledge graph is the **triple**: a subject, a predicate and an object, such as (Marie Curie, awarded, Nobel Prize in Physics). Subjects and objects are nodes; predicates are labelled, directed edges. Two main data models are used.

The **RDF** model treats every fact as a triple, with entities and relations identified by globally unique identifiers. Graphs in this model are typically queried with SPARQL, a pattern-matching language in which a query describes a subgraph shape with variables to be filled in. An **ontology** or schema defines classes, such as Person or City, and the relations allowed between them, and can support logical inference, for example deriving that a capital city is also a city.

The **property graph** model, used by many graph databases, allows both nodes and edges to carry key-value properties, such as a start date on an employment edge. Property graphs are queried with languages such as Cypher or Gremlin.

Large public knowledge graphs contain hundreds of millions or billions of facts about general-world entities. Enterprise and domain graphs are smaller but model specific concepts such as products, customers, genes or legal provisions.

## Question Answering over Knowledge Graphs

Knowledge base question answering (KBQA) maps a natural-language question to an answer drawn from the graph. Two broad approaches exist.

**Semantic parsing** translates the question into a formal query, such as SPARQL or Cypher, which is then executed against the graph. The question "Who directed the film that won Best Picture in a given year?" becomes a query that finds the film with that award and year and then follows the directed-by relation. Early systems used hand-written grammars and templates; later ones used sequence-to-sequence neural models, and LLMs can now generate graph queries from a schema description and a few examples. Semantic parsing gives precise, explainable answers but fails when the parse is wrong or when the question uses terms that do not map cleanly onto the schema.

**Retrieval-based** or **embedding-based** approaches avoid producing an explicit query. They identify the entities mentioned in the question, extract a subgraph around them, and score candidate answer nodes using learned representations. Knowledge graph embedding methods, such as translational models that represent a relation as a vector offset between the subject and object embeddings, allow approximate reasoning and can infer missing links that are not stored explicitly.

Both approaches depend on **entity linking**, the step of matching mentions in the question, such as "Curie" or "the French capital", to specific nodes in the graph. Linking errors are a major source of failure, particularly for ambiguous names.

## Multi-Hop Traversal

Many useful questions require combining several facts. "Which university did the doctoral advisor of a given physicist attend?" requires finding the physicist, following the advisor edge to a second person, and then following an educated-at edge to a university. Each step is a **hop**.

Knowledge graphs are well suited to such questions because each hop is an explicit edge traversal with a defined relation type. A graph query can express a fixed multi-hop path directly. For questions where the path is not known in advance, systems search over possible relation paths from the topic entity, using learned scoring to decide which edges to follow and pruning unpromising branches. Graph neural networks propagate information along edges over several layers, allowing each node's representation to reflect its multi-hop neighbourhood.

The difficulty grows with the number of hops. The number of reachable nodes can increase exponentially, especially through highly connected hub nodes such as countries or common categories. Errors compound, since a wrong choice at an early hop leads to a wrong final answer. Incompleteness is a further challenge: real-world graphs are missing many true facts, so a required edge may simply not exist.

Text-based retrieval systems handle multi-hop questions less directly. A single retrieval step rarely returns all the needed passages, because the second document may share no vocabulary with the original question. Iterative retrieval, which retrieves, extracts an intermediate entity, and retrieves again, imitates graph traversal over text but is slower and more error-prone.

## Graph-Based versus Semantic Retrieval

Semantic retrieval embeds text chunks and finds those closest to the query in vector space. It differs from graph-based retrieval in several respects.

- **Precision and structure.** Graphs return exact facts and support constraints, aggregation and comparison, such as counting entities or filtering by date. Semantic retrieval returns passages that are topically similar, which may or may not contain the specific fact.
- **Coverage.** Text corpora capture nuance, explanation and long-tail information that is hard to fit into a schema. Graphs capture only what has been extracted and modelled.
- **Multi-hop reasoning.** Graphs make relation chains explicit; semantic retrieval struggles when intermediate entities are not mentioned in the question.
- **Construction cost.** Graphs require schema design, entity resolution and ongoing curation or extraction pipelines. Vector indexes can be built directly from raw documents.
- **Explainability.** A graph answer can be justified by the exact path traversed. Semantic retrieval justifies answers by pointing to source passages.
- **Robustness to wording.** Semantic retrieval tolerates paraphrase well. Graph approaches depend on correctly mapping the question onto entities and relation types.

## Hybrid Approaches

Because the two approaches have complementary strengths, many systems combine them. In **graph-augmented RAG**, an LLM or extraction pipeline builds a graph of entities and relations from a document collection. At query time, the system identifies relevant entities, expands to their neighbourhood in the graph, and gathers the linked text passages or community summaries as context for the generator. This helps with questions that require connecting information spread across many documents, and with broad, corpus-level questions such as identifying the main themes in a collection.

Other hybrids link graph nodes to their source passages, so that a graph traversal can be followed by semantic retrieval within the documents attached to the visited nodes. Query routers may also decide per question whether a structured graph query, a semantic search, or both are most likely to give a good answer.

## Summary

Knowledge graphs represent facts as entities and typed relations, queried with languages such as SPARQL or Cypher. Question answering over them uses semantic parsing into formal queries or embedding-based scoring of candidate answers, both of which depend on entity linking. Graphs are particularly effective for multi-hop questions because relation chains are explicit, though they suffer from incompleteness and growth in the search space. Semantic retrieval over text offers broad coverage and robustness to wording but weaker structure. Hybrid systems that combine graph traversal with semantic retrieval increasingly exploit the strengths of both.
