# Approximate Nearest Neighbour Search

Nearest neighbour search is the problem of finding, among a large set of vectors, those closest to a query vector under some distance or similarity measure. It underlies dense retrieval, recommendation, image search, deduplication and many other applications built on learned embeddings. Exact search becomes too slow and memory-intensive as collections grow to millions or billions of high-dimensional vectors, so practical systems rely on approximate nearest neighbour (ANN) methods that trade a small loss in accuracy for large gains in speed and memory. This article covers the problem setting, the three most widely used families of techniques (graph-based indexes such as HNSW, inverted file indexes, and product quantization), and the tradeoffs between recall, latency, memory and build cost.

## Problem Setting

Given a collection of N vectors in d dimensions and a query vector q, k-nearest neighbour search returns the k vectors closest to q. Common measures are Euclidean (L2) distance, inner product and cosine similarity. Cosine similarity is equivalent to inner product on unit-normalized vectors, and maximum inner product search can be reduced to Euclidean search with a simple transformation, so most libraries support all three.

A brute-force scan computes N distances per query, at a cost proportional to N times d. With optimized matrix operations on GPUs this is feasible for collections up to a few million vectors, and it serves as the ground truth against which approximate methods are judged. Classical space-partitioning structures such as k-d trees work well in low dimensions but degrade toward brute-force performance as dimensionality rises, a consequence of the curse of dimensionality: in high dimensions, distances between random points concentrate, and partitions fail to prune most of the space.

ANN quality is usually reported as **recall@k**: the fraction of the true k nearest neighbours that appear in the returned k results. Speed is measured as queries per second or as latency percentiles. Every ANN index exposes parameters that move along a curve between these two.

## Graph-Based Indexes: HNSW

Graph-based methods build a proximity graph in which each vector is a node connected to some of its near neighbours. Search starts at an entry node and greedily moves to whichever neighbour is closer to the query, continuing until no neighbour improves the result.

**Hierarchical Navigable Small World (HNSW)** is the most widely used graph index. It organizes nodes into multiple layers. Every node appears in the bottom layer, and each node is assigned to higher layers with exponentially decreasing probability, so upper layers are sparse. Search begins at the top layer, where long-range links allow quick movement across the space, and descends layer by layer, refining the position at each level. At the bottom layer a best-first search with a candidate list finds the final neighbours. This structure is loosely analogous to a skip list.

HNSW has three main parameters. **M** sets the number of links per node; larger values improve recall and robustness but increase memory and build time. **efConstruction** is the size of the candidate list used while inserting nodes; larger values yield a higher-quality graph at greater build cost. **efSearch** is the candidate list size at query time and is the main knob for trading recall against latency.

HNSW delivers excellent recall at low latency and supports incremental insertion, which makes it a common default in vector databases. Its drawbacks are high memory use, since full vectors and graph links are usually kept in RAM, and difficulty with deletions, which are often handled by marking nodes as deleted and periodically rebuilding.

## Inverted File Indexes: IVF

The **inverted file (IVF)** approach partitions the vector space into clusters. During training, k-means is run on a sample of the data to produce nlist centroids. Each vector is assigned to its nearest centroid and stored in that centroid's list. At query time, the query is compared with all centroids, the nprobe closest lists are selected, and only vectors in those lists are scanned.

If the data is divided into nlist roughly equal clusters and nprobe lists are searched, the fraction of vectors scanned is about nprobe divided by nlist. Increasing **nprobe** raises recall because true neighbours that lie just across a cluster boundary are more likely to be found, at the cost of more distance computations. A common rule of thumb sets nlist on the order of the square root of N.

IVF indexes use less memory than graph indexes, build quickly once centroids are trained, and map naturally to disk-based or distributed storage because each list can be stored and loaded independently. They need a representative training sample, and recall can suffer if the data distribution shifts after training.

## Product Quantization

Memory is often the binding constraint at large scale. A billion 768-dimensional float32 vectors require about 3 terabytes. **Product quantization (PQ)** compresses vectors to a few dozen bytes each.

PQ splits each d-dimensional vector into m sub-vectors of d/m dimensions. For each subspace, k-means learns a codebook of typically 256 centroids. Each sub-vector is replaced by the index of its nearest centroid, which fits in one byte, so a vector is stored as m bytes. With m = 64, a 768-dimensional float vector shrinks from 3,072 bytes to 64 bytes.

Distances are computed without decompressing. For a given query, the distance from each query sub-vector to every centroid in the corresponding codebook is precomputed into a lookup table. The approximate distance to any stored vector is then the sum of m table lookups. This is called asymmetric distance computation, because the query stays exact while the database vectors are quantized.

PQ is lossy, so the ranking of close candidates can be wrong. A common remedy is **re-ranking**: retrieve a larger candidate set using compressed codes, then recompute exact distances for those candidates using full-precision vectors stored on disk or in a secondary tier. **Scalar quantization**, which stores each dimension as an 8-bit or 4-bit integer, is a simpler alternative with less compression and less accuracy loss.

## Composite Indexes

These techniques are frequently combined. **IVF-PQ** uses IVF for coarse partitioning and PQ to compress vectors within each list, often encoding the residual between a vector and its centroid for better accuracy. This combination supports billion-scale search on a single machine. HNSW can also be used over IVF centroids to speed up the coarse assignment step, or over PQ-compressed vectors to reduce memory. Disk-oriented graph indexes keep a compressed copy of the vectors in memory for navigation and full vectors on SSD for final re-ranking.

## Recall and Latency Tradeoffs

Choosing an ANN configuration means balancing several factors:

- **Recall versus latency.** Raising efSearch in HNSW or nprobe in IVF increases recall with diminishing returns. Moving from 90 to 95 percent recall is usually cheap; moving from 99 to 99.9 percent can cost several times more latency.
- **Memory versus accuracy.** Quantization cuts memory dramatically but introduces distance errors, partly recovered by re-ranking.
- **Build time and updates.** HNSW builds slowly but supports insertion; IVF builds fast but may need retraining as data changes.
- **Filtering.** Restricting results by metadata, such as date or access permissions, interacts badly with ANN pruning. Post-filtering can return too few results when the filter is selective, and pre-filtering can break graph connectivity, so many systems use filter-aware traversal or partition by common filter values.

For retrieval-augmented generation, moderate recall loss at the first stage is often acceptable, because a reranker or the generator can tolerate a few missing candidates, while latency directly affects user experience.

## Summary

Approximate nearest neighbour search makes vector similarity search practical at scale by accepting small recall losses. HNSW builds a layered proximity graph with excellent recall and latency but high memory use. IVF partitions vectors into clusters and scans only the nearest few. Product quantization compresses vectors into compact codes with fast table-based distance computation. Composite indexes combine these methods, and tuning parameters such as efSearch, nprobe and code size determines where a system sits on the recall, latency and memory tradeoff.
