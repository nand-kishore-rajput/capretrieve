# Rank Fusion: Combining Ranked Lists

Rank fusion, also called data fusion or result merging, is the problem of combining several ranked lists of documents into a single ranking. The lists may come from different retrieval models applied to the same collection, such as BM25 and a dense retriever, from different query formulations, or from entirely different sources in a federated or metasearch system. Fusion is attractive because different systems tend to retrieve overlapping sets of relevant documents but different sets of non-relevant ones, so agreement between systems is evidence of relevance. This article describes the main families of fusion methods: score normalization, the classic CombSUM and CombMNZ operators, rank-based methods including Reciprocal Rank Fusion, and practical considerations when applying them.

## Why Fusion Works

Two effects are commonly cited to explain the gains from fusion. The **chorus effect** holds that when several independent systems rank a document highly, it is more likely to be relevant than a document favoured by only one system. The **skimming effect** holds that each system's top results contain its most reliable judgments, so merging the tops of several lists gathers relevant documents that any single system might have missed. Fusion helps most when the input systems are individually reasonable and make different errors, as with lexical and semantic retrievers.

## The Score Comparability Problem

Different retrieval models produce scores on different scales. BM25 scores are unbounded and depend on query length and collection statistics. Cosine similarities lie between minus one and one but often cluster in a narrow band. Cross-encoder outputs may be logits or probabilities. Even the same model can produce very different score ranges for different queries. Adding raw scores across systems would let whichever system has the largest range dominate. Score-based fusion therefore requires **normalization** first.

## Score Normalization

**Min-max normalization** rescales each list to the interval from zero to one:

normalized = (s - min) / (max - min)

where min and max are the lowest and highest scores in that list for the current query. It is simple and widely used. Its weaknesses are sensitivity to outliers, since one extreme score compresses all the others, and the fact that the top document in every list receives a score of one regardless of how good it actually is. A weak list with uniformly poor matches is promoted to the same scale as a strong list.

**Z-score normalization** subtracts the mean and divides by the standard deviation of the scores in the list:

normalized = (s - mean) / std

This expresses each score as the number of standard deviations above or below the list average. It is less sensitive to a single extreme value than min-max and preserves information about how far a document stands out from the rest. However, it assumes a roughly bell-shaped distribution, and retrieval scores are often skewed, with a few high-scoring documents and a long tail. The statistics also depend on how many results were retrieved.

Other variants include **sum normalization**, which divides each score by the total in the list, and normalizations that use a fixed theoretical range for a model's scores rather than per-query statistics. More advanced approaches fit separate probability distributions to the scores of relevant and non-relevant documents and convert scores into estimated probabilities of relevance, which are then comparable across systems.

## CombSUM and CombMNZ

The classic fusion operators work on normalized scores. For a document d and a set of input lists:

- **CombSUM** adds up the document's normalized scores across all lists. A document missing from a list contributes zero for that list.
- **CombMNZ** multiplies the CombSUM value by the number of lists in which the document appears with a non-zero score. This explicitly rewards documents retrieved by many systems, strengthening the chorus effect.
- **CombMAX** and **CombMIN** take the highest or lowest score, and **CombANZ** averages over only the lists that contain the document. These are generally less effective than CombSUM and CombMNZ.

CombSUM and CombMNZ have been strong and robust in many evaluations. Their effectiveness depends heavily on the normalization method, and the best pairing varies across collections. **Weighted** variants multiply each system's scores by a weight reflecting its expected quality, typically tuned on held-out queries. In hybrid lexical and dense retrieval, a common form is a convex combination: alpha times the normalized dense score plus one minus alpha times the normalized sparse score.

## Rank-Based Fusion

Rank-based methods ignore scores entirely and use only each document's position in each list, avoiding the normalization problem.

**Borda count**, borrowed from voting theory, gives each document points according to its position, for example N minus rank plus one for a list of length N, and sums points across lists. **Condorcet** methods rank documents by pairwise majority preferences across the input lists.

**Reciprocal Rank Fusion (RRF)** has become the most widely used rank-based method. Each document receives the score

RRF(d) = sum over lists of 1 / (k + rank(d))

where rank(d) is the document's position in the list, starting at one, and k is a constant. Documents absent from a list contribute nothing for that list. The constant k, set to 60 in the original proposal and commonly left at that value, controls how quickly the contribution decays with rank. A small k gives the very top positions much more weight; a large k flattens the curve so that positions further down still matter. With k = 60, the first-ranked document contributes about 0.0164 and the tenth about 0.0143, so agreement across lists matters more than exact position.

RRF has several practical advantages. It needs no score normalization and no training, works across sources with arbitrary and incomparable scores, and is robust to a single poorly calibrated system. It has performed competitively with, and often better than, more elaborate learned methods. For these reasons, many search engines and vector databases provide RRF as their default hybrid search fusion method. Its main limitation is that it discards score magnitudes: a document that one system ranks first with overwhelming confidence is treated the same as one ranked first by a narrow margin. Weighted RRF, which multiplies each list's contribution by a per-source weight, partly addresses differences in source quality.

## Practical Considerations

- **List depth.** Fusion considers only documents in the retrieved lists. Retrieving deeper lists from each system, for example the top 100 instead of the top 10, gives fusion more overlap to work with at the cost of more retrieval work.
- **Correlated inputs.** Fusing very similar systems, such as two dense models trained on the same data, brings smaller gains than fusing diverse ones.
- **Per-source caps.** In multi-source systems, limiting how many documents each source contributes before or after fusion stops a source that returns many results from crowding out others.
- **Fusion then reranking.** A common pipeline fuses candidates from multiple retrievers with RRF to maximize recall, then applies a cross-encoder reranker to the fused top candidates to maximize precision.
- **Learned fusion.** Learning-to-rank models can use scores, ranks and source features as inputs, but they need labelled training data and may generalize poorly to new sources.

## Summary

Rank fusion merges ranked lists from multiple systems and exploits the fact that relevant documents tend to be retrieved by several systems. Score-based fusion requires normalization, with min-max and z-score as the most common choices, each with distinct weaknesses. CombSUM adds normalized scores and CombMNZ additionally rewards documents found by more systems. Rank-based fusion avoids normalization; Reciprocal Rank Fusion, which sums 1 / (k + rank) with k typically 60, is simple, training-free and robust, and has become a standard method for hybrid and multi-source retrieval.
