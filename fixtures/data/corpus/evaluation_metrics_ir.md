# Evaluation Metrics for Information Retrieval and RAG

Evaluation is central to information retrieval (IR). Without reliable measurements, it is impossible to tell whether a new ranking model, index configuration or fusion method is actually better than the old one. Classical IR evaluation measures how well a system ranks relevant documents for a set of test queries. Retrieval-augmented generation (RAG) adds a second layer, since the final output is a generated answer whose quality depends on both retrieval and generation. This article describes the test collection methodology, set-based and rank-based retrieval metrics including precision and recall at k, MRR, MAP and nDCG, and the main dimensions used to judge RAG answers, notably faithfulness and answer relevance.

## Test Collections and Relevance Judgments

The standard approach to offline evaluation, often called the Cranfield paradigm, uses a test collection made up of three parts: a document corpus, a set of queries (often called topics), and **relevance judgments** (qrels) indicating which documents are relevant to each query. Judgments may be **binary**, relevant or not, or **graded**, for example on a scale from 0 (not relevant) to 3 (highly relevant).

Judging every document for every query is impractical for large collections, so evaluation campaigns use **pooling**: the top results from many participating systems are merged and only those are judged. Documents outside the pool are assumed non-relevant. This introduces bias against new systems that retrieve relevant documents that no earlier system found, which is one reason why metrics robust to unjudged documents have been studied.

Metrics are computed per query and then averaged across queries. Because performance varies widely between queries, comparisons between systems should use statistical significance tests, such as paired t-tests or randomization tests, over the per-query scores.

## Precision and Recall at k

**Precision** is the fraction of retrieved documents that are relevant. **Recall** is the fraction of all relevant documents that are retrieved. For ranked results, both are usually computed at a cutoff k:

- **Precision@k** = (number of relevant documents in the top k) / k
- **Recall@k** = (number of relevant documents in the top k) / (total number of relevant documents for the query)

Precision@k reflects what a user sees on the first page of results. Recall@k matters for first-stage retrieval in multi-stage pipelines, where the aim is to get relevant candidates into the set passed to a reranker or generator; in RAG, recall at the number of passages fed to the model directly limits whether the answer can be correct. The two typically trade off as k changes: increasing k raises recall but usually lowers precision.

Neither metric accounts for order within the top k. A list with the relevant document at position 1 scores the same as one with it at position k. **Hit rate@k**, also called success@k, simply records whether at least one relevant document appears in the top k.

## Mean Reciprocal Rank

**Reciprocal rank** is 1 divided by the position of the first relevant document. If the first relevant result is at rank 1 the score is 1, at rank 2 it is 0.5, at rank 4 it is 0.25, and if no relevant document is retrieved it is 0. **Mean reciprocal rank (MRR)** averages this over queries, often with a cutoff such as MRR@10.

MRR suits tasks where the user needs only one good answer, such as known-item search, factoid question answering or navigational queries. It ignores all relevant documents after the first, so it is not suitable when several relevant results are valuable.

## Mean Average Precision

**Average precision (AP)** for a single query is the mean of precision@k taken at each rank k where a relevant document appears, divided by the total number of relevant documents. Relevant documents that are never retrieved contribute a precision of zero. AP therefore rewards systems that retrieve all relevant documents and place them near the top. **Mean average precision (MAP)** averages AP over queries.

MAP combines precision and recall into a single number and has long been a standard metric in IR evaluation campaigns. It assumes binary relevance and depends on knowing the full set of relevant documents, which makes it sensitive to incomplete judgments.

## Normalized Discounted Cumulative Gain

**Discounted cumulative gain (DCG)** supports graded relevance and models the fact that users are less likely to look at lower-ranked results. Each document contributes a gain based on its relevance grade, discounted by a function of its position:

DCG@k = sum for i from 1 to k of gain(rel_i) / log2(i + 1)

The gain is either the relevance grade itself or 2^rel - 1, which emphasizes highly relevant documents more strongly. The logarithmic discount means a document at rank 1 counts fully, one at rank 3 counts half as much, and so on.

Raw DCG is not comparable across queries because queries have different numbers of relevant documents. **Normalized DCG (nDCG)** divides DCG@k by the ideal DCG@k, the value obtained by sorting all judged documents in order of decreasing relevance. nDCG therefore ranges from 0 to 1, where 1 means the ranking is ideal up to position k. nDCG@10 is one of the most widely reported metrics for modern retrieval benchmarks, including zero-shot evaluations across many domains.

## Online and User-Centred Evaluation

Offline metrics are complemented by online evaluation with real users. A/B tests compare systems on behavioural signals such as click-through rate, time to success, reformulation rate and abandonment. Interleaving merges results from two systems into one list and infers preference from which system's results receive clicks, which is more sensitive than A/B testing for the same amount of traffic. Behavioural signals are noisy and biased by position, so they are typically debiased or combined with offline judgments.

## Evaluating RAG Answers

In a RAG system, good retrieval does not guarantee a good answer, and the generated text must be evaluated directly. Common dimensions include:

**Faithfulness** (also called groundedness) measures whether every claim in the answer is supported by the retrieved context. A typical procedure decomposes the answer into atomic statements and checks each against the context with a natural language inference model or an LLM judge; the score is the fraction of supported statements. Faithfulness is about consistency with the evidence provided, not about absolute truth: an answer can be faithful to an incorrect passage.

**Answer relevance** measures whether the answer actually addresses the question, regardless of correctness. An answer that is accurate but off-topic, incomplete or padded with irrelevant material scores low. One automated approach generates questions from the answer and measures their semantic similarity to the original question.

**Context relevance** or **context precision** measures how much of the retrieved context is relevant to the question, while **context recall** measures whether the retrieved context contains all the information needed for a reference answer. These link answer quality back to retrieval quality and help locate failures.

**Answer correctness** compares the answer with a reference answer, using exact match or token-level F1 for short factoid answers, or semantic similarity and LLM-based judgment for longer answers.

**Citation quality** checks whether cited sources actually support the statements they are attached to, and whether all statements that need support have citations.

**LLM-as-judge** methods are widely used to score these dimensions at scale. They correlate reasonably with human ratings but show biases, including preference for longer answers, sensitivity to the order in which candidates are presented, and favouritism toward outputs similar to their own style. Good practice includes clear scoring rubrics, randomized ordering, periodic calibration against human judgments, and reporting the judge model used.

## Summary

IR evaluation relies on test collections of queries, documents and relevance judgments, with metrics averaged over queries and compared with significance tests. Precision@k and recall@k measure set quality at a cutoff, MRR focuses on the first relevant result, MAP summarizes precision across all relevant documents, and nDCG handles graded relevance with a position discount. RAG evaluation adds answer-level dimensions, chiefly faithfulness to the retrieved context and relevance to the question, alongside context precision and recall, correctness and citation quality, often scored with LLM judges that must themselves be validated.
