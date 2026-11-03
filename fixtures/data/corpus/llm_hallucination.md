# Hallucination in Large Language Models

In the context of large language models (LLMs), hallucination refers to generated content that is fluent and plausible but is not supported by the provided input or by established facts. Examples include invented citations, wrong dates or figures, non-existent software functions, and summaries that add details absent from the source. Hallucination is one of the main obstacles to deploying LLMs in settings where accuracy matters, such as medicine, law, finance and technical support. This article reviews the causes of hallucination, the common ways of classifying it, methods for detecting it, and strategies for mitigating it, with particular attention to retrieval grounding.

## Causes

Hallucination arises from several interacting factors across data, training and inference.

**Training objective.** LLMs are trained to predict the next token given previous tokens. This objective rewards producing text that is statistically likely, not text that is true. When the model lacks the relevant knowledge, the most likely continuation is often a confident-sounding guess, because confident answers are far more common than admissions of ignorance in typical training text.

**Data issues.** Pre-training corpora contain errors, outdated information, contradictions and fiction. Facts that appear rarely in the data are learned poorly, so models are most likely to hallucinate about obscure entities, the "long tail" of knowledge. Knowledge is also frozen at the training cutoff, so questions about later events invite fabrication.

**Fine-tuning and alignment.** Instruction tuning and preference optimization can reward helpful-seeming, complete answers. If human raters or reward models prefer detailed responses, the model may learn to produce details even when it is uncertain. Fine-tuning on facts the model did not already know may also encourage it to generate unsupported content more generally.

**Decoding.** Sampling with high temperature increases diversity but also the chance of selecting a low-probability, incorrect token. Once an error is generated, later tokens are conditioned on it, and the model tends to stay consistent with its own earlier output, a phenomenon sometimes called snowballing.

**Context handling.** Even when correct information is in the prompt, the model may overlook it, especially in long contexts, or may prefer its parametric knowledge over the supplied text when the two conflict.

## Taxonomy

Several overlapping classifications are in common use.

**Intrinsic versus extrinsic.** Originating in summarization research, this distinction separates outputs that contradict the source (intrinsic) from outputs that add information that cannot be verified from the source (extrinsic). Extrinsic content may happen to be true, but it is still unsupported.

**Factuality versus faithfulness.** Factuality hallucinations conflict with real-world knowledge, for example stating the wrong capital of a country. Faithfulness hallucinations depart from the user's instructions or the provided context, for example answering a different question or ignoring a retrieved document. A response can be factual but unfaithful, or faithful to a flawed source but not factual.

**By content type.** Practical taxonomies group errors by what is fabricated: entities, numbers and dates, citations and references, quotations, code and APIs, or reasoning steps. Reasoning hallucinations involve logically invalid steps even when the individual facts are right.

## Detection

Detecting hallucination automatically is difficult, but several families of methods exist.

**Reference-based checking.** When a source document or retrieved context is available, each claim in the output can be compared with it. Natural language inference (NLI) models classify whether the source entails, contradicts or is neutral toward each claim. Question-generation approaches generate questions from the output, answer them from the source, and compare the answers.

**Claim decomposition.** Long outputs are split into atomic factual claims, each of which is verified separately against a knowledge source or search results. The fraction of supported claims serves as a factual precision score.

**Uncertainty estimation.** Token probabilities or entropy can signal uncertainty, although raw probabilities are not always well calibrated, especially after alignment tuning. Sampling-based consistency methods generate several responses to the same prompt and measure agreement; claims that vary across samples are more likely to be hallucinated, while knowledge the model actually holds tends to be reproduced consistently.

**LLM-as-judge.** A second model, or the same model with a different prompt, evaluates whether a response is supported by the evidence. This is flexible and widely used in practice but inherits the biases and errors of the judging model.

**Internal-state probes.** Research has shown that classifiers trained on a model's hidden activations can sometimes predict whether a statement it produces is true, suggesting that models carry internal signals of uncertainty not always reflected in their output.

## Mitigation

**Retrieval grounding.** Retrieval-augmented generation supplies relevant documents at inference time and instructs the model to answer from them. This addresses missing and outdated knowledge directly and makes outputs verifiable through citations. Its effectiveness depends on retrieval quality: irrelevant or wrong passages can introduce new errors, and the model must be encouraged to rely on the context rather than its prior. Good practice includes reranking for precision, asking the model to quote or cite specific passages, and instructing it to say when the context does not contain the answer.

**Abstention and calibration.** Training or prompting the model to express uncertainty or decline to answer reduces confident fabrication. Reward schemes that penalize wrong answers more than abstentions encourage this behaviour.

**Decoding strategies.** Lower temperature or greedy decoding reduces random errors for factual tasks. Contrastive decoding methods compare token distributions, for example between different layers of the model or between the output with and without the context, to amplify grounded predictions.

**Self-verification.** The model drafts an answer, generates verification questions about its own claims, answers them independently, and revises the draft. Chain-of-thought prompting can improve reasoning accuracy, though it can also produce plausible but flawed reasoning.

**Training interventions.** Fine-tuning on data that rewards factual precision, curated high-quality corpora, and preference optimization that favours supported and appropriately hedged answers all reduce hallucination rates.

**Tool use and post-hoc correction.** Models can call calculators, code interpreters, databases or search engines for facts they would otherwise guess. Post-hoc pipelines detect unsupported claims and either remove them or rewrite them using retrieved evidence.

## Remaining Difficulties

No method eliminates hallucination. Detection tools have their own error rates, and evaluation benchmarks cover only part of the space of real use. There is also an inherent tension between creativity, where generating new content is desired, and factuality, where it is not. Grounding helps most for knowledge-intensive questions with good sources, and helps least when sources are missing, conflicting or of poor quality.

## Summary

Hallucination in LLMs stems from a next-token objective that rewards plausibility, imperfect and frozen training data, alignment pressures toward complete answers, decoding randomness and imperfect use of context. It is classified as intrinsic or extrinsic and as factuality or faithfulness errors. Detection relies on entailment checking, claim verification, consistency sampling and model-based judges. Mitigation combines retrieval grounding, abstention, careful decoding, self-verification, training changes and tool use, with retrieval grounding being one of the most effective and widely deployed approaches for knowledge-intensive tasks.
