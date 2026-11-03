---
tags: [reading, books, papers]
date: 2025-10-12
---

# Reading List

Everything I want to read, am reading, or have finished, with a line or two on what stuck. Papers relevant to the master's thesis get a ⭐ and also go into [[Thesis Ideas]]. General background on models lives in [[Large Language Models]]. #reading

Status legend: **done**, **reading**, **queued**, **dropped**

## Currently reading

- **Designing Data-Intensive Applications**, *reading*, chapter 9 of 12
  - Second time through. The replication and consistency chapters make much more sense now that I've been on call for two years.
  - Take: "exactly once" is almost always "at least once plus idempotency". Wish I'd internalised this before the 2023 billing incident.
- **Why We Sleep**, *reading*, about halfway
  - Started after the sleep tracker showed me averaging 5h50 in September.
  - Take: some claims feel overstated, but the bit about consistent wake times is easy to act on. Trying a fixed 6:45 alarm, even on weekends without Mila.
- **Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks** ⭐, *reading*
  - The original RAG paper. Reading it properly this time instead of skimming the abstract.
  - Take: the retriever and generator are trained jointly, which almost nobody does in practice anymore. Interesting angle for the thesis.

## Tech and AI

- **Attention Is All You Need** ⭐, *done* (2025-03)
  - Finally read it start to finish. Shorter than I remembered.
  - Take: the multi-head part is the real trick. Positional encoding still feels hacky to me.
- **Dense Passage Retrieval for Open-Domain Question Answering** ⭐, *done* (2025-05)
  - Take: in-batch negatives are a cheap, strong baseline. Will use this as a comparison in my experiments.
- **Lost in the Middle: How Language Models Use Long Contexts** ⭐, *done* (2025-06)
  - Take: put the most relevant chunks at the start or the end of the prompt. Directly useful at work and for the thesis.
- **BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models** ⭐, *queued*
  - Need this for the evaluation chapter. Supposed to show BM25 is still hard to beat out-of-domain.
- **ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction** ⭐, *queued*
- **Self-RAG: Learning to Retrieve, Generate, and Critique** ⭐, *queued*
  - Relevant to the "when should the system retrieve at all" question in my thesis.
- **The Pragmatic Programmer**, *done* (2024-11)
  - Take: still good. "Don't live with broken windows" applies to my flat right now too.
- **Staff Engineer: Leadership Beyond the Management Track**, *dropped* (2025-08)
  - Dropped after the PIP started. Not the right moment to read about promotions. Maybe later.
- **Database Internals**, *queued*
  - For the vector index chapters. Want to understand LSM trees properly before comparing HNSW implementations.

## Health and body

- **Built to Move**, *done* (2025-04)
  - Ten simple physical habits. Take: the sit-to-stand test without hands is humbling. I failed it.
  - Practical result: floor sitting while reading to Mila in the evenings.
- **Back Mechanic**, *done* (2025-02)
  - Recommended by the physio. Take: the "big three" exercises (curl-up, side plank, bird dog) every morning, 10 minutes. Back has been noticeably better since March.
- **Outlive**, *reading*, slowly
  - Take so far: zone 2 cardio matters more than I thought. Doing 3 × 40 minutes a week on the bike now.
- **The Obesity Code**, *queued*
  - Background reading for the intermittent fasting experiment. Skeptical, want to read it critically.
- **Breath**, *dropped*
  - Too anecdotal for me. Got the key idea (nasal breathing) from the first two chapters.

## Personal, life, the hard stuff

- **Mom's House, Dad's House**, *done* (2025-03)
  - Recommended by the Jugendamt counsellor. Take: kids need two real homes, not one home and one visit. That's what pushed me to ask for more than every other weekend.
- **Two Homes** (picture book), *done*, read with Mila (2025-04)
  - She asked for it four nights in a row. That told me more than any conversation.
- **Never Split the Difference**, *re-reading*
  - For the severance talks. Take: labelling emotions and calibrated "how" questions. "How am I supposed to accept that?" is going on a sticky note.
- **Getting to Yes**, *done* (2025-09)
  - Take: separate the people from the problem, focus on interests not positions. Useful for both the divorce and the job. My BATNA in each case needs to be clear before I walk in.
- **Man's Search for Meaning**, *done* (2025-01)
  - Read it in the first weeks after moving out. Take: you can't always choose what happens, but you can choose how you respond. Helped more than I expected.
- **Four Thousand Weeks**, *queued*
  - A friend recommended it when I said I'm trying to do work, a master's, and single parenting at the same time.
- **Your Money or Your Life**, *queued*
  - Want to rethink the budget from first principles once the settlement is done.

## Stats (2025 so far)

- Books finished: 11 (goal: 18, not going to happen, fine)
- Papers read properly: 9 (goal: 24 before thesis registration)
- Dropped: 3. Getting better at dropping things without guilt.

## Rules for myself

1. Max 3 things in *reading* at once.
2. One paper a week minimum, Sunday mornings while Mila is at Jana's.
3. Write the take within 24 hours of finishing, otherwise it's gone.
4. Fiction counts. I haven't read a novel since 2024. Need to fix that over Christmas.
