---
tags: [transformers, attention, ml]
date: 2025-01-19
---

# Transformer Attention

Study notes from the deep learning module, rewritten so future me can actually follow them. I always nod along to attention explanations and then fail to reproduce the maths a week later. This is the fix. #transformers

## Why attention at all

Before transformers, sequence models were mostly RNNs and LSTMs. They read tokens one at a time and squash the history into a hidden state. Two problems: long-range dependencies fade, and you can't parallelise across the sequence during training.

Attention lets every token look directly at every other token in one step. No recurrence, fully parallel, and the path between any two positions has length one. The original transformer paper's whole pitch was basically "drop recurrence, keep attention".

## Scaled dot-product attention

For each token we compute three vectors from its embedding with learned weight matrices:

- **Query (Q)**: what am I looking for?
- **Key (K)**: what do I contain, for matching purposes?
- **Value (V)**: what do I hand over if someone attends to me?

Then:

`Attention(Q, K, V) = softmax(Q K^T / sqrt(d_k)) V`

Step by step:

1. Dot every query with every key, giving an n by n score matrix.
2. Divide by `sqrt(d_k)`. Without this, the dot products grow with dimension, the softmax saturates, and gradients vanish. This is the bit I always forget.
3. Softmax each row so the weights sum to one.
4. Weighted sum of values.

My intuition: it's a soft, differentiable dictionary lookup. The query is fuzzy-matched against all keys and you get a blend of the values.

## Self-attention vs. cross-attention

- **Self-attention**: Q, K and V all come from the same sequence. Each token builds a context-aware representation of itself.
- **Cross-attention**: queries come from one sequence (decoder), keys and values from another (encoder output). Used in translation-style encoder-decoder models.
- **Causal (masked) self-attention**: in decoder-only models, token i may only attend to positions up to i. Implemented by setting future scores to minus infinity before the softmax. This is what makes autoregressive generation work in [[Large Language Models]].

## Multi-head attention

Instead of one attention with big vectors, split into h heads, each with its own smaller Q, K, V projections. Run attention in parallel, concatenate, project back.

Why bother:

- Different heads can specialise: one tracks syntax, another coreference, another position.
- Same total compute as a single big head, since each head has dimension `d_model / h`.

Honest note: the "heads specialise" story is partly true and partly post-hoc storytelling. Lots of heads can be pruned with little loss.

Variants worth knowing:

- **Multi-query attention**: all heads share one K and V. Much smaller KV cache, faster inference.
- **Grouped-query attention**: middle ground, groups of heads share K and V. Seems to be the default in recent open models.

## Positional information

Attention by itself is permutation-invariant: shuffle the tokens and you get the same outputs (shuffled). So position has to be injected.

- Original approach: fixed sinusoidal encodings added to embeddings.
- Learned absolute position embeddings: simple, but don't extrapolate past training length.
- Rotary embeddings: rotate Q and K by a position-dependent angle so the dot product depends on relative distance. Widely used now and part of why context extension tricks work.

## Complexity

This is the part relevant to my retrieval work.

- Time and memory for the score matrix are **O(n^2 · d)** and **O(n^2)** in sequence length n.
- Double the context, quadruple the attention cost.
- During generation, the KV cache grows linearly with context length per layer and per head, which is often the real memory bottleneck.

Ways people get around it:

- **FlashAttention**: same maths, but tiles the computation to avoid materialising the full n by n matrix in slow memory. Exact, not an approximation. Huge practical speedup.
- **Sparse / sliding-window attention**: each token only attends locally plus a few global tokens.
- **Linear attention variants**: kernel tricks to avoid the softmax over all pairs. Usually some quality loss.

#attention

## How this connects to retrieval

Quadratic cost is one reason I think retrieval stays relevant even as context windows grow. Selecting five good chunks is cheaper than attending over five hundred mediocre ones, and attention spread over a huge context gets diluted anyway.

## Open questions

- Why exactly do models struggle with the middle of long contexts? Is it the positional encoding, training data distribution, or attention sinks at the start?
- Can I build a toy visualisation of attention weights over a retrieved chunk to see what the model actually reads?

## TODO

- [ ] Implement single-head attention in NumPy from scratch, no peeking.
- [ ] Extend to multi-head with masking and check shapes by hand.
- [ ] Rederive why the scaling factor is `sqrt(d_k)` (variance argument).
