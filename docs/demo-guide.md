# Demo guide

How to show CapRetrieve to a team in about ten minutes, using the `/demo`
page and the demo data in `fixtures/data/`.

## Before the meeting

1. **Pin the models.** `openrouter/free` routes each call to a random free
   model: plans change between runs, calls can take minutes, and free
   models are capped at 50 requests a day on accounts with under $10 of
   credit. In `.env`:

   ```
   ANALYZER_MODEL=anthropic/claude-haiku-5.5
   SYNTHESIS_MODEL=anthropic/claude-haiku-5.5
   ```

   A question costs roughly $0.002 with Haiku, and $10 of OpenRouter credit
   covers thousands of runs. Each request reserves `LLM_MAX_TOKENS` of
   output, so an almost empty balance is rejected even for cheap models.

2. **Start the server** and open http://localhost:8000/demo:

   ```bash
   .venv/bin/uvicorn capretrieve.api.main:app --port 8000
   ```

3. **Run each demo question once.** This confirms the answers, and the
   first query also warms the vault and index. Save each result page
   (Cmd+S) as a fallback in case the network or provider fails during the
   meeting.

## The story in five questions

Click the example buttons on the page in this order. Each one shows a
different routing decision.

| # | Button | Question | What to point at |
|---|--------|----------|------------------|
| 1 | Literature lookup | "What does the literature say about intermittent fasting and energy levels?" | Only the document corpus is selected. The other two are allowed but score below the cut-off. No over-selection. |
| 2 | Linked notes | "What other notes link to my project retrospective, and what did those say?" | `relational: yes` and starting note `project retrospective`. Chroma is **blocked** with `paradigm_mismatch`: only link-following search can answer this. Web is blocked too, usually with `privacy_leak`, because the privacy check runs first and personal notes count as sensitive. The evidence is the retrospective and its linked notes. |
| 3 | Health data stays local | "My HbA1c came back at 7.2 last week…" | Privacy `confidential`. Web search is blocked with `privacy_leak`, even though the question asks for current guidelines. |
| 4 | Confidential deal | "We agreed 40 million for Project Falcon. Has anything leaked in the press yet?" | The strongest pull toward the web: it literally asks about the press. Web scored best on paradigm and freshness and is still blocked. The answer comes from the confidential note. |
| 5 | Needs live web | "Has the European Commission published any updates to the AI Act's general-purpose AI code of practice this month?" | Nothing private, so web search is selected. The privacy rule isn't simply "never use the web". (The vault is also selected, because it declares `live` freshness; see known issues in [future-work.md](future-work.md).) |

Talking points:

- **The LLM never picks the source.** Section 1 of the page is everything the
  LLM decided: a handful of typed values. Section 2 is the planner applying
  rules to them, and every block shows its exact rule.
- **Before/after for question 4.** With a free model as the analyzer,
  this question was sent to the web in 3 of 3 runs, because that model
  didn't flag it as confidential. With Claude as the analyzer it is blocked
  every time. The rule never changed; the planner can only enforce what the
  analyzer reports. That is the system's main limitation, and worth saying
  out loud.
- **Evaluation numbers:** 95% routing accuracy over 80 runs, 98% on held-out
  scenarios, and 0 of 40 privacy-sensitive runs sent to the web, against 13
  of 40 for an LLM told the same privacy rule (see
  [positioning.md](positioning.md)).
- **Adding a source is configuration plus one class** (see
  [adding-a-connector.md](adding-a-connector.md)). Open
  `configs/connectors/web_search.yaml` to show how small a manifest is.

## Questions to avoid live

- **S1, "search the web… my divorce settlement".** The web is blocked
  correctly, but the vault is usually not selected, so the answer can say
  it found nothing (see [future-work.md](future-work.md)).
- **"Metformin warnings this year"**: routes correctly to the web, but the
  answer depends on what Tavily returns and can be thin.

## If something goes wrong

| What you see | Cause | Fix |
|---|---|---|
| `500` with `429` in the server log | Free-model rate limit or daily cap | Pin a paid model, or add credit |
| `500` with `402` in the server log | Balance too low for the `max_tokens` reservation | Add credit, or lower `LLM_MAX_TOKENS` |
| `500` with `EmptyCompletionError` | A reasoning model spent `max_tokens` before answering | Raise `LLM_MAX_TOKENS` or pin a non-reasoning model |
| `500` with `ReadTimeout` | The model took longer than 30 seconds | Pin a faster model |
| Web search returns nothing useful | No `WEB_SEARCH_API_KEY`, so Tavily runs keyless and rate-limited | Set a Tavily key |

`/trace/view?query=…&token=…` shows the same trace as a static page if you
want to share a link. It needs `TRACE_VIEW_TOKEN` from `.env`.
