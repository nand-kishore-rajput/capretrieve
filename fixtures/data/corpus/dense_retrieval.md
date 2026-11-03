# Dense and Sparse Retrieval

Text retrieval is the task of finding, from a large collection, the documents or passages most relevant to a query. For decades the dominant methods were sparse, lexical models built on term matching and inverted indexes. Since the arrival of pre-trained transformer encoders, dense retrieval, which represents queries and documents as continuous vectors and ranks by vector similarity, has become a strong alternative. This article compares the two paradigms, explains the bi-encoder architecture, describes DPR-style contrastive training and the role of hard negatives, and discusses why BM25 remains an important baseline.

## Sparse Retrieval

Sparse retrieval represents a text as a high-dimensional vector with one dimension per vocabulary term. Almost all entries are zero because any given text uses only a small fraction of the vocabulary. Relevance is computed from overlapping terms, and an inverted index maps each term to the list of documents that contain it, which makes search over millions of documents fast.

**TF-IDF** weights a term by its frequency in the document multiplied by the inverse of how many documents contain it, so that rare, discriminative terms count for more. **BM25** refines this with two important adjustments. Term frequency saturates, controlled by a parameter usually called k1, so that the tenth occurrence of a word adds much less than the first. Document length is normalized, controlled by a parameter b, so that long documents are not favoured merely for containing more words. Typical default values are k1 between 1.2 and 2.0 and b around 0.75.

Sparse methods have clear strengths. They need no training data, are interpretable, handle exact matches of rare terms, names, identifiers and codes very well, and are cheap to index and update. Their main weakness is the **vocabulary mismatch** problem: a relevant document that uses different words, such as "automobile" for "car" or a paraphrase of the query, gets little or no score.

**Learned sparse** models such as SPLADE keep the sparse, inverted-index-friendly representation but use a transformer to predict term weights and to expand documents and queries with related terms. They narrow the gap with dense models while keeping much of the efficiency of lexical search.

## Dense Retrieval

Dense retrieval encodes each query and document as a vector of a few hundred to a few thousand real-valued dimensions. Relevance is the inner product or cosine similarity between the two vectors. Because the encoder is trained to place semantically related texts near each other, dense retrieval can match paraphrases and synonyms that share no surface terms.

Search is performed with nearest neighbour search over document vectors. Exact search compares the query with every document, which is too slow for large collections, so approximate nearest neighbour indexes such as HNSW, IVF and product quantization are used in practice.

## The Bi-Encoder Architecture

A **bi-encoder**, also called a dual encoder or two-tower model, uses separate encoder passes for the query and the document. Each is typically a BERT-style transformer, with the final representation taken from the special classification token or from mean pooling over token embeddings. The query and document encoders may share weights or be trained separately.

The key property of a bi-encoder is that document representations do not depend on the query. All documents can be encoded once, offline, and stored in an index. At query time only the query needs encoding, followed by a fast vector search. This is what makes dense retrieval practical as a first-stage retriever.

The tradeoff is expressiveness. Because the query and document never interact inside the model, a single vector must summarize everything about a document that might matter for any future query. **Cross-encoders**, which process the query and document together, are more accurate but must run once per query-document pair, so they are used for reranking a short candidate list rather than for first-stage retrieval. **Late-interaction** models such as ColBERT keep one vector per token and compute a sum of maximum similarities between query and document tokens, offering a middle ground at the cost of a much larger index.

## DPR-Style Training

Dense Passage Retrieval (DPR) established a simple and effective training recipe for open-domain question answering. Training data consists of questions paired with passages that contain the answer. The model is trained with a contrastive objective: for each question, the encoder should give the positive passage a higher similarity score than a set of negative passages. The loss is the negative log-likelihood of the positive passage under a softmax over the scores of the positive and all negatives.

An efficient technique is the use of **in-batch negatives**. In a batch of B question-passage pairs, each question's positive passage serves as a negative for the other B minus 1 questions. This gives many negatives per question at almost no extra cost, since all passage embeddings in the batch are already computed. Larger batches provide more negatives and usually improve results, which has led to techniques for increasing the effective batch size, such as gradient caching and cross-device negative sharing.

## Hard Negatives

Random or in-batch negatives are often easy to tell apart from the positive because they are about entirely different topics. A model trained only on easy negatives learns coarse topical similarity but struggles with fine distinctions. **Hard negatives** are passages that look relevant but do not answer the question.

Common sources of hard negatives include the top results from BM25 that do not contain the answer, which DPR used alongside in-batch negatives, and the top results from an earlier version of the dense retriever itself. Iterative schemes periodically re-mine hard negatives with the current model as training proceeds, so that the negatives stay challenging.

Hard negatives carry a risk of **false negatives**: passages that are in fact relevant but were not labelled as such. Training the model to push these away can hurt quality. Mitigations include filtering candidate negatives with a cross-encoder and discarding those it scores as highly relevant, and **distillation**, where the bi-encoder learns to match the score distribution of a stronger cross-encoder teacher rather than hard binary labels.

## BM25 as a Baseline

Despite the progress of dense models, BM25 remains a demanding baseline. On benchmarks that test **zero-shot** retrieval across many domains, dense retrievers trained on one dataset have often failed to beat BM25 on unfamiliar domains, especially those with specialized terminology such as biomedical or legal text. BM25 is also robust on queries that depend on exact strings, such as product codes, error messages and rare names, where dense embeddings can blur distinctions.

For these reasons, **hybrid retrieval** is common in practice. The system runs BM25 and a dense retriever in parallel and merges their ranked lists, often with Reciprocal Rank Fusion or a weighted combination of normalized scores. The two methods make different errors, so the combination is usually better than either alone. BM25 is also widely used as a source of candidates and of hard negatives when training dense models.

## Summary

Sparse retrieval matches terms through inverted indexes and is fast, interpretable and strong on exact matches, but it suffers from vocabulary mismatch. Dense retrieval encodes queries and documents as vectors with bi-encoders, allowing semantic matching and offline document indexing. DPR-style training uses contrastive loss with in-batch negatives, and hard negatives mined from BM25 or the model itself sharpen fine-grained discrimination, with care needed to avoid false negatives. BM25 remains a strong baseline, especially out of domain, and hybrid systems that combine sparse and dense retrieval are a common and effective choice.
