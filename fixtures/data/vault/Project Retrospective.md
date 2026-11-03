---
tags: [work, retrospective, project-atlas, q2-2025]
date: 2025-07-04
---

# Project Retrospective

Quarterly retrospective for **Project Atlas** (migrating the billing service off the old monolith and onto the event-driven pipeline). Covers Q2 2025, i.e. sprints 14 to 19. Written up the evening after the 3-hour retro session with the team (Lena, Tobias, Priya, Jonas, Markus as observer for the last hour). #retro #atlas

These are my personal notes, not the sanitized version that went on the team wiki.

## Context

- Team size: 5 engineers, 1 PM (shared with another team), 0.5 QA
- Original target: billing reads fully cut over by 31 May
- Actual: reads cut over 26 June, writes still dual-running at 70/30
- Budgeted effort: 180 story points across 6 sprints. Delivered: 141. Carried over: 39.
- Incidents: 2 (one Sev-2 on 12 May, invoices duplicated for ~340 customers; one Sev-3 on 3 June, delayed reconciliation report)

## What went well

- **Feature flags everywhere.** Every cutover step was behind a flag. When the Sev-2 hit we flipped back to the monolith path in under 8 minutes. That alone justified the extra week we spent building the flag service in sprint 14.
- **Shadow traffic.** Running the new consumer in shadow mode for 10 days caught 23 mismatches before any customer saw them. Most were rounding issues in VAT on cross-border invoices (19% vs 7% edge cases).
- **Pairing on the hard bits.** Priya and I paired on the idempotency layer for almost all of sprint 16. Slower on paper, but zero bugs found in that component since.
- **Runbooks.** Jonas wrote runbooks for every alert before we went live. During the 12 May incident the on-call person (Tobias, 2 months on the team) followed it step by step without paging anyone else.
- **Review culture got better.** Average PR review time dropped from 31 hours in sprint 14 to 9 hours in sprint 19. We started doing two fixed review slots per day (10:00 and 15:30).
- Long design review sessions stopped wrecking me physically. Since switching to the [[Standing Desk]] in April I can get through a 2-hour architecture review alternating sitting and standing without being stiff for the rest of the day. Small thing, but it changed how I felt about these sessions.

## What didn't go well

- **Estimates were wildly optimistic.** The event schema work was sized at 13 points and took nearly three sprints. Details and patterns in [[Estimation Mistakes]], this needs its own note.
- **Sprint planning was too crowded.** We kept committing to 32 to 35 points when our real velocity was about 24. Planning meetings ran 2.5 hours and still ended with unclear acceptance criteria. Process thoughts in [[Sprint Planning]].
- **Dependency on the Platform team.** We waited 11 working days for Kafka topic provisioning in May. Nobody had flagged it as a risk in the kickoff.
- **The Sev-2.** Root cause: the dedup key used invoice number only, not invoice number + tenant ID. Two tenants share a numbering scheme. We had a test for it. It was skipped (`@Disabled` since sprint 15 because it was "flaky"). Nobody noticed.
- **Communication with Finance.** They found out about the duplicate invoices from customers before they heard it from us. Embarrassing. Took 4 hours to send the internal notice.
- **My own part:** I took on too much coordination work and my coding output dropped. I closed 6 tickets in Q2 compared to 14 in Q1. Worth thinking about how that looks from the outside.

## Numbers I want to remember

| Metric | Q1 | Q2 |
|---|---|---|
| Velocity (avg points/sprint) | 26 | 23.5 |
| Deploys to prod | 18 | 41 |
| Rollbacks | 1 | 4 |
| Mean time to recovery | 47 min | 12 min |
| Open bugs at quarter end | 17 | 22 |

Deploy frequency more than doubled, MTTR dropped a lot. Bug count went up, which is partly just because we touched so much code.

## Action items

Agreed in the room, with owners:

1. **Re-enable all disabled tests** and add a CI check that fails if a test is disabled for more than 14 days. Owner: Tobias. Due: 18 July.
2. **Cap sprint commitment at 85% of trailing 3-sprint velocity.** Owner: me (I run planning). Starts sprint 20.
3. **Risk register at kickoff** with explicit cross-team dependencies and a named contact per dependency. Owner: Lena.
4. **Incident comms template** for Finance and Support, with a 60-minute target for the first internal notice. Owner: Jonas.
5. **Spike before sizing** anything that touches schemas or contracts. Max 2 days per spike. Owner: whole team.
6. **Retro follow-up at the offsite.** We will review progress on items 1 to 5 during the engineering block at [[Team Offsite 2025]] and decide whether Atlas write cutover moves to Q3 or Q4.

## Personal takeaways

- I need to protect at least 2 focus blocks a week for actual engineering work, not just coordinating.
- Write down decisions the same day. Half the arguments in the retro were about what we "agreed" in April.
- The team is genuinely good. The project slipped because of planning and dependencies, not because anyone slacked.
- Next retro: ask Markus to join from the start or not at all. Him walking in for the last hour changed the tone of the room completely. People went quiet about the Platform team delays.

## Open questions

- Should we split Atlas into two projects (reads done, writes as "Atlas 2")? Psychologically it might help the team to close something.
- Do we keep the 0.5 QA or push for a full person? The Sev-2 argues for full.
- How do we measure whether action item 2 actually helped? Proposal: track commitment vs completion ratio for 4 sprints, target above 0.9.
