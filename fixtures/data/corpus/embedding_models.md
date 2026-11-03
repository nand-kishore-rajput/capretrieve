# Sentence Embedding Models

A sentence embedding model maps a piece of text, whether a short phrase, a sentence, a paragraph or a whole document, to a fixed-length vector of real numbers. The goal is that texts with similar meaning lie close together in this vector space, so that semantic similarity can be measured with simple operations such as cosine similarity. Sentence embeddings power semantic search, retrieval-augmented generation, clustering, deduplication, classification and recommendation. This article covers the evolution of embedding models, the contrastive training methods that produce them, the role of dimensionality, and techniques for adapting embeddings to specialized domains.

## From Word Vectors to Sentence Encoders

Early distributed representations assigned one vector per word, learned from co-occurrence statistics in large corpora. Methods such as word2vec and GloVe captured useful relations between words, but sentence representations built by averaging word vectors ignored word order and context, so "dog bites man" and "man bites dog" received the same vector.

Contextual language models such as BERT produce a different vector for each token depending on its surroundings. However, using raw BERT outputs as sentence embeddings, either from the classification token or by averaging token vectors, works poorly for similarity tasks. The pre-training objectives, masked language modelling and next-sentence prediction, do not encourage a geometry in which cosine similarity reflects meaning. Raw BERT embeddings are also anisotropic: they occupy a narrow cone of the space, so almost all pairs show high cosine similarity.

The key advance was to fine-tune transformer encoders specifically for sentence similarity. Sentence-BERT (SBERT) placed BERT in a siamese network, encoding two sentences with shared weights, pooling each into a single vector, and training on labelled sentence pairs from natural language inference and semantic similarity datasets. The resulting embeddings could be compared with cosine similarity, making large-scale semantic search practical with bi-encoders instead of slow pairwise cross-encoders.

## Architecture and Pooling

Most modern embedding models are transformer encoders, although decoder-only language models are increasingly adapted as embedding models as well. A pooling step reduces the sequence of token vectors to one vector. **Mean pooling** averages all token vectors and is the most common choice for encoder models. **CLS pooling** uses the vector of a special first token. For decoder-only models, **last-token pooling** is often used, because under causal attention only the final token has seen the whole input. Embeddings are usually L2-normalized so that inner product equals cosine similarity.

Input length is limited by the model's context window, commonly 512 tokens for older encoders and several thousand for newer ones. Longer documents must be chunked, and long inputs can dilute the embedding when they cover many topics.

Some models are **instruction-tuned** or use task prefixes, prepending a short description such as "query:" or "passage:" or a natural-language task instruction, so that a single model can produce embeddings suited to retrieval, clustering or classification. Using the wrong prefix, or none, can noticeably reduce quality.

## Contrastive Training

Contrastive learning is the dominant training approach. The model is shown pairs of texts that should be similar (positives) and is trained to place them closer together than texts that should be dissimilar (negatives).

The standard loss is **InfoNCE**, also called multiple negatives ranking loss. For a batch of anchor-positive pairs, each anchor is compared with its own positive and with the positives of every other anchor in the batch, which act as **in-batch negatives**. Similarities are divided by a **temperature** parameter and passed through a softmax, and the loss is the negative log-probability of the true positive. A lower temperature sharpens the distribution and puts more emphasis on hard negatives. Because each additional batch item supplies another negative, larger batches usually improve results.

Training commonly proceeds in stages:

1. **Weakly supervised pre-training** on very large collections of naturally occurring pairs, such as titles and bodies, questions and answers from forums, or queries and clicked results. These datasets are noisy but provide hundreds of millions of examples covering many domains.
2. **Supervised fine-tuning** on smaller, high-quality labelled datasets for retrieval, entailment and similarity, often with **hard negatives** mined by retrieving passages that appear relevant but are not.
3. **Distillation** from a cross-encoder or a large language model, where the embedding model learns to match the teacher's relevance scores.

**Unsupervised** variants also exist. One simple method feeds the same sentence through the encoder twice with different dropout masks and treats the two outputs as a positive pair, which produces surprisingly strong embeddings without labelled data.

Synthetic data generated by large language models, such as generated queries for unlabelled passages, is now widely used to expand training sets into new tasks and languages.

## Dimensionality

Embedding dimensions commonly range from 384 to over 4,000. Higher dimensions can store more information and often score better on benchmarks, but they raise storage, memory and search costs linearly. A collection of 10 million documents at 1,024 float32 dimensions needs about 40 gigabytes for vectors alone.

Several techniques reduce this cost:

- **Matryoshka representation learning** trains the model so that the first m dimensions of an embedding form a useful embedding on their own, for several values of m. Users can truncate vectors, for example from 1,024 to 256 dimensions, with modest loss in quality.
- **Quantization** stores each dimension as an 8-bit integer or even as a single bit. Binary embeddings shrink storage by a factor of 32 and allow very fast Hamming distance search, usually followed by re-scoring with higher-precision vectors.
- **Dimensionality reduction** such as principal component analysis can be applied after training, though it is generally less effective than training with truncation in mind.

Smaller dimensions are not always worse in practice: a well-trained compact model can beat a poorly matched larger one on a specific task.

## Domain Adaptation

General-purpose embedding models are trained mostly on web text and may perform poorly on specialized domains such as law, medicine, finance, scientific literature or source code, where vocabulary, abbreviations and notions of relevance differ. Common adaptation techniques include:

- **Fine-tuning on in-domain pairs.** Even a few thousand labelled query-passage pairs can bring large gains.
- **Synthetic query generation.** A language model generates plausible queries for passages in the target corpus, creating training pairs without manual labelling. Filtering generated pairs with a cross-encoder improves their quality.
- **Continued pre-training** of the underlying encoder on unlabelled domain text, using masked language modelling or contrastive objectives, before similarity fine-tuning.
- **Pseudo-labelling with a cross-encoder**, where a stronger reranker scores candidate pairs and the embedding model is trained to reproduce those scores.
- **Hybrid search.** Combining embeddings with lexical retrieval such as BM25 compensates for domain terms that the embedding model handles poorly.

A risk of fine-tuning is **catastrophic forgetting**, where gains in the target domain come with losses elsewhere. Mixing general data into training batches and using moderate learning rates reduce this effect. Evaluation should use in-domain test queries, since public benchmark rankings do not always predict domain performance.

## Summary

Sentence embedding models map text to fixed-length vectors whose geometry reflects meaning. Raw contextual models such as BERT need fine-tuning for this purpose, typically in a siamese bi-encoder with pooling. Contrastive training with InfoNCE, in-batch negatives, hard negatives and multi-stage pipelines produces strong general models. Dimensionality trades quality against cost, and techniques such as Matryoshka learning and quantization reduce storage. Domain adaptation through in-domain fine-tuning, synthetic queries, continued pre-training and hybrid search improves performance on specialized corpora.
