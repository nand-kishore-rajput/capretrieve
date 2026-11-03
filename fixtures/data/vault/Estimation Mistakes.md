---
tags: [work, estimation, lessons-learned]
date: 2025-07-08
---

# Estimation Mistakes

A running list of estimates I (or we) got badly wrong, why, and what I'd do differently. Started after the Q2 retro, where estimation came up as the root cause of most of our slippage. Context in [[Project Retrospective]]. I'm keeping this honest, including my own calls. #estimation #lessons

## The worst offenders

### 1. Event schema for invoices (Atlas, sprint 15)

- **Estimated:** 13 points, roughly 1 sprint for one person
- **Actual:** 2.5 sprints, two people for part of it, about 34 points of real effort
- **Ratio:** 2.6x
- **Why it blew up:**
  - We assumed one schema. It turned into four: invoice created, line item added, credit note issued, invoice voided.
  - Schema registry compatibility rules (BACKWARD_TRANSITIVE) meant every change had to be versioned, which nobody on the team had done before.
  - Finance wanted the VAT breakdown per line item, not per invoice. We learned this in week 2.
- **Lesson:** anything touching a contract between systems gets a spike first. No exceptions.

### 2. Dedup / idempotency layer (sprint 16)

- **Estimated:** 5 points
- **Actual:** about 13 points
- **Why:** I sized it based on a library I'd used at a previous job. The library didn't support our Postgres version. We wrote it ourselves.
- **Lesson:** "I've done this before" is only useful if the environment is the same. Check versions before sizing.

### 3. Kafka topic provisioning (May)

- **Estimated:** 0 points ("Platform does that")
- **Actual:** 11 working days of waiting, plus 2 days of my time chasing it
- **Why:** external dependency, no named contact, no ticket in their queue until we asked.
- **Lesson:** dependencies are not free just because someone else does the work. Put a calendar estimate on them, even if the points are zero.

### 4. "Quick" reconciliation report (sprint 18)

- **Estimated:** 3 points
- **Actual:** 8 points
- **Why:** the report needed data from both the old and new pipeline during dual-running. Joining them turned out to be the whole problem.
- **Lesson:** during a migration, everything that reads data is twice as hard because there are two sources of truth.

### 5. Test cleanup after the Sev-2 (sprint 17)

- **Estimated:** 2 points
- **Actual:** 2 points
- Including this because it went *right*. Small, well-defined, done by someone who knew the code. That's what a good estimate looks like.

## Patterns I see

Going through about 40 tickets from Q1 and Q2 in a spreadsheet on 6 July:

| Ticket type | Avg estimate | Avg actual | Ratio |
|---|---|---|---|
| Bug fix, known area | 2.1 | 2.4 | 1.1x |
| New endpoint, existing service | 4.8 | 6.0 | 1.25x |
| Data migration / backfill | 5.3 | 12.7 | 2.4x |
| Schema or contract change | 7.5 | 18.9 | 2.5x |
| Cross-team dependency | 1.0 | n/a (calendar time) | – |

So the pattern is clear: we're fine at small, local work. We're terrible at anything involving data shape or other teams.

## Why we keep doing this

- **Anchoring.** The first number someone says in planning poker sticks. Usually it's the most senior person, often me.
- **Optimism about unknowns.** We size the part we can see and treat the unknown part as zero.
- **Pressure.** There's an unspoken expectation from above that Atlas should be "done". Smaller numbers feel safer in the moment. They aren't.
- **No feedback loop.** Until this note, nobody compared estimates to actuals. We just moved on to the next sprint.
- **Points as time.** Even though we say points are complexity, everyone silently converts 1 point to about half a day.

## Rules I'm trying now

1. **Ratio multiplier by category.** For migration and schema work, multiply the gut estimate by 2 before saying it out loud. Ugly, but it's data-based.
2. **Spike first** for anything with an unknown external system. Timebox 2 days.
3. **Say the number last.** In poker I reveal after everyone else, so I don't anchor the juniors.
4. **Write the assumptions down** in the ticket. "Assumes one schema", "Assumes library X works on PG 14". When an assumption breaks, re-estimate openly.
5. **Calendar time for dependencies.** A separate field in the ticket for "waiting on others", tracked in days.
6. **Revisit monthly.** Update the table above on the first Monday of each month.

## Things I said that I want to remember not to say again

- "That's a two-day thing." (It was eight.)
- "We'll just reuse what we did for the order service." (We couldn't.)
- "Platform will have it ready by Thursday." (They didn't know about it.)
- "It's basically the same as the last migration." (It never is.)

## Monthly check-ins

**2025-08-04** – Ratio for migration tickets in July: 1.7x. Better than 2.4x. The spike rule is helping. One schema ticket still came in at 3x because Finance changed the requirement mid-sprint.

**2025-09-01** – Ratio 1.5x for migration work. Committed vs done above 0.9 for 4 sprints in a row. Nobody upstairs has commented on it, which tells me what they're actually measuring.
