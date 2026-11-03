---
tags: [prompting, llm, json]
date: 2025-05-11
---

# Prompt Engineering

A grab bag of what works, what doesn't, and what I keep relearning when prompting [[Large Language Models]]. Mostly from building the routing component and the answer step of my side project. #prompting

## General stance

I'm a bit allergic to the "magic phrase" style of prompt engineering. Most real gains come from being clear, giving examples, and constraining the output. Treat the prompt like an API spec for a very capable but very literal colleague who has never seen your project.

## Patterns that actually help

- **Role plus task plus constraints**: one sentence on who the model is, a clear statement of the task, then explicit rules. Short beats clever.
- **Few-shot examples**: three to five input/output pairs covering edge cases. For classification (like "which source should answer this?") examples help more than any amount of instruction text.
- **Delimit inputs**: wrap user content and retrieved chunks in clear markers like `<context>` and `<question>` tags. Reduces confusion between instructions and data, and helps a bit against injection.
- **Ask for reasoning before the answer** when the task needs thought. Put the reasoning field *before* the decision field in structured output, otherwise the model decides first and rationalises after.
- **Give an escape hatch**: "If the context does not contain the answer, reply with NOT_FOUND." Without this, models invent answers.
- **Specify the audience and format**: "three bullet points, no preamble" saves a lot of trimming.
- **Put long context first, question last**: in my tests the model follows the question better when it's at the end.

## Structured JSON output

This is where I spend most of my time, because the router needs machine-readable decisions.

What I want back, for example:

```json
{
  "reasoning": "Query mentions my own notes on sleep, private data",
  "sources": ["vault"],
  "needs_fresh_data": false,
  "confidence": 0.86
}
```

Lessons:

- **Use native structured output or tool calling when available.** Schema-constrained decoding beats "please respond in JSON" by a mile. Parse failures drop to almost zero.
- **Keep schemas flat and small.** Deeply nested objects with optional fields produce weird outputs.
- **Use enums for categorical fields.** `"sources"` should only allow known values. Free text here means fuzzy-matching garbage later.
- **Validate anyway.** Run a schema validator on every response and have a fallback (retry once, then default to a safe route like local-only).
- **Don't trust self-reported confidence.** The `confidence` number is decoration; it's not calibrated. I keep it for logging, not decisions.
- **Strip code fences** if the API doesn't support constrained output; models love wrapping JSON in triple backticks.
- **Watch the field order.** As above: reasoning first, decision last.

#json

## Pitfalls I've walked into

- **Over-long system prompts**: I once had a 1,500-word system prompt with conflicting rules. The model followed whichever rule was most recent. Cut it to 300 words and quality went up.
- **Negative instructions**: "Do not mention the web" sometimes *primes* mentioning the web. Phrase positively when possible: "Only use the provided context."
- **Prompt injection via retrieved content**: a web page containing "ignore previous instructions" is a real risk once you pipe web search results into the prompt. Delimit, and never let retrieved text trigger tool calls on its own.
- **Example leakage**: few-shot examples bias outputs towards their specific content. If all examples route to "web", guess what happens.
- **Temperature confusion**: I had temperature 0.7 on a classification prompt for weeks and wondered why routing was flaky.
- **Changing the model, keeping the prompt**: prompts don't transfer cleanly between models. Re-test after every model switch.
- **Evaluating by vibes**: tweaking a prompt and trying two queries is not evaluation. Keep a fixed test set and rerun it on every change.

## A template I keep reusing

1. One-line role.
2. Task description, two or three sentences.
3. Rules as a numbered list.
4. Output schema.
5. Few-shot examples.
6. Delimited context.
7. Delimited question.

Boring, reliable.

## Open questions

- Is chain-of-thought still worth it for small routing decisions, or does it just add latency and tokens? Need an A/B on my test set.
- How do I version prompts properly? Right now they're strings in Python files, and I lose track of which version produced which results.
- Can a router prompt explain *why* a source is excluded (privacy, staleness) in a way that's useful for debugging?

## TODO

- [ ] Move prompts into separate template files with version ids.
- [ ] Add schema validation plus a single retry to the router.
- [ ] Collect ten injection-style strings and test the answer prompt against them.
- [ ] Compare zero-shot vs. five-shot routing accuracy.
