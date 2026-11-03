# The Transformer Attention Mechanism

The transformer is a neural network architecture built around attention rather than recurrence or convolution. Introduced for machine translation, it became the foundation of nearly all modern large language models, as well as many vision, speech and multimodal systems. Its central operation, self-attention, lets every position in a sequence gather information directly from every other position in a single step. This article explains scaled dot-product attention, multi-head attention, positional encodings, the quadratic cost of attention in sequence length, and the main families of efficient-attention methods developed to reduce that cost.

## From Recurrence to Attention

Before transformers, sequence models were dominated by recurrent neural networks such as LSTMs and GRUs. These process tokens one after another, carrying a hidden state forward. Two problems follow. First, computation is sequential, which limits parallelism on modern hardware. Second, information from distant tokens must pass through many intermediate steps, which makes long-range dependencies hard to learn. Attention mechanisms were first added to recurrent encoder-decoder models so the decoder could look back at all encoder states. The transformer took the further step of removing recurrence altogether and building the whole model from attention and position-wise feed-forward layers.

## Scaled Dot-Product Attention

Attention is defined in terms of three matrices: queries Q, keys K and values V. Each row of these matrices corresponds to one token and is produced by multiplying the token's representation by a learned projection matrix. For a sequence of n tokens with key dimension d_k, the attention output is

Attention(Q, K, V) = softmax(Q K^T / sqrt(d_k)) V

The product Q K^T is an n by n matrix of similarity scores: entry (i, j) measures how much token i's query matches token j's key. Applying softmax across each row turns the scores into weights that sum to one. Multiplying by V then produces, for each token, a weighted average of the value vectors of all tokens.

The division by the square root of d_k is the "scaled" part. If the components of queries and keys are independent with zero mean and unit variance, their dot product has variance d_k. For large d_k the raw scores become large in magnitude, pushing the softmax into regions where it is nearly one-hot and its gradients are very small. Scaling keeps the variance near one and training stable.

In **self-attention**, Q, K and V all come from the same sequence. In **cross-attention**, used in encoder-decoder models, queries come from the decoder while keys and values come from the encoder output. In autoregressive decoders, a **causal mask** sets the scores for future positions to negative infinity before the softmax, so each token can attend only to itself and earlier tokens. This makes it possible to train on whole sequences in parallel while still modelling left-to-right generation.

## Multi-Head Attention

A single attention operation computes one set of weights per token pair, which limits the kinds of relationships it can represent at once. Multi-head attention runs h attention operations in parallel, each with its own learned projections for Q, K and V into a lower-dimensional subspace of size d_model / h. The outputs of the heads are concatenated and passed through a final linear projection.

Different heads can specialize. Analyses of trained models have found heads that track syntactic relations, heads that attend to the previous token, heads that copy repeated patterns, and heads with broad, diffuse attention. Because each head works in a smaller subspace, the total computational cost is similar to that of a single full-width head.

Variants change how keys and values are shared. Multi-query attention uses one shared key and value projection for all query heads, and grouped-query attention shares keys and values within groups of heads. Both reduce the size of the key-value cache kept during autoregressive inference, which lowers memory bandwidth requirements and speeds up generation with little loss in quality.

## The Transformer Block

A standard transformer layer combines multi-head attention with a position-wise feed-forward network, usually two linear layers with a non-linearity such as ReLU or GELU, expanding to about four times the model width and projecting back. Each sublayer is wrapped in a residual connection and layer normalization. The original design applied normalization after the residual addition; most modern large models use pre-normalization, applying it before each sublayer, which tends to make deep networks easier to train. Stacking dozens of these layers gives the full model.

## Positional Encodings

Attention by itself is permutation-equivariant: shuffling the input tokens shuffles the outputs in the same way, so the model has no built-in notion of order. Positional information must be added explicitly.

The original transformer used fixed **sinusoidal encodings**, where each dimension of the position vector is a sine or cosine of the position at a different frequency. These are added to the token embeddings. A fixed offset between two positions corresponds to a linear transformation of their encodings, which in principle helps the model reason about relative distance. **Learned absolute embeddings**, used in BERT and early GPT models, treat each position as a trainable vector but cannot be used beyond the maximum length seen in training.

**Relative position** methods encode the distance between tokens rather than absolute indices. **Rotary position embedding (RoPE)** rotates pairs of query and key dimensions by an angle proportional to position, so that the dot product between a query and a key depends only on their relative offset. RoPE is used in many current open-weight LLMs and can be extended to longer contexts by rescaling its frequencies. **ALiBi** adds a fixed, head-specific linear penalty to attention scores in proportion to distance, which also helps with extrapolation to longer sequences than those seen in training.

## Quadratic Complexity

The score matrix Q K^T has n squared entries. Computing it takes time proportional to n squared times d, and a straightforward implementation stores it in memory proportional to n squared per head. Doubling the context length therefore roughly quadruples the cost of the attention layers. For short sequences the feed-forward layers dominate the cost, but at the context lengths now common in LLMs, from tens of thousands to over a million tokens, attention becomes the bottleneck. During autoregressive generation, the key-value cache also grows linearly with context length and must be read at every step.

## Efficient-Attention Variants

Many methods aim to reduce this cost. They fall into a few families.

**Sparse attention** restricts each token to a subset of positions. Sliding-window or local attention lets each token attend only to a fixed window of neighbours, giving cost linear in n. Patterns that mix local windows with a few global tokens, or with strided or dilated connections, allow information to propagate across the whole sequence over several layers.

**Low-rank and kernel approximations** avoid forming the full n by n matrix. Low-rank methods project keys and values to a shorter length. Linear attention replaces the softmax with a kernel feature map so that the product can be reordered as Q (K^T V), reducing cost to linear in n. These methods are efficient but usually lose some accuracy compared with exact softmax attention.

**IO-aware exact attention**, best known through FlashAttention, computes exact softmax attention but restructures the computation into tiles that fit in fast on-chip GPU memory, using an online softmax so that the full score matrix is never written to slower high-bandwidth memory. The arithmetic is still quadratic, but memory use becomes linear and wall-clock speed improves substantially. This approach is now standard in training and inference.

**Alternative architectures** such as state-space models and modern recurrent designs replace attention with operations that scale linearly with sequence length, sometimes in hybrid models that keep a few attention layers.

## Summary

Scaled dot-product attention computes softmax-weighted averages of value vectors, with scaling by the square root of the key dimension to keep training stable. Multi-head attention runs several such operations in parallel subspaces, and grouped-query variants reduce inference memory. Because attention ignores order, positional information is supplied by sinusoidal, learned, rotary or bias-based schemes. The quadratic cost of attention in sequence length motivates sparse, low-rank, kernel-based and IO-aware methods, of which IO-aware exact attention has become the most widely used.
