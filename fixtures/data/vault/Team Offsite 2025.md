---
tags: [work, offsite, planning]
date: 2025-07-24
---

# Team Offsite 2025

Engineering offsite for the Billing and Payments group, 22 to 24 July 2025, at a seminar hotel near Lake Starnberg. 23 people total: two engineering teams, PMs, design, our director Claudia Rehm for day 1, and Markus for all three days. #offsite #planning

My notes, taken mostly on paper and typed up on the train home.

## Logistics

- **Travel:** S-Bahn plus a shuttle bus, about 1h15m from the office
- **Budget:** about 14,000 EUR total (rooms, meeting space, catering, one team dinner)
- **Rooms:** I shared with nobody, thankfully. Wi-Fi was bad in the main room, fine in the lobby
- **Pre-reading:** Q2 retro summary, draft Q3 OKRs, Atlas status deck (I made this one, 12 slides)

## Agenda

### Day 1 – Tuesday 22 July

- 10:00 Arrival, coffee
- 10:30 Claudia: "Where the company is going" (45 min)
- 11:30 Team retros shared across teams, 15 min each. I presented the Atlas retro from [[Project Retrospective]].
- 13:00 Lunch
- 14:00 Workshop: Q3 objectives, first draft
- 16:30 Walk around the lake
- 19:00 Dinner

### Day 2 – Wednesday 23 July

- 09:00 Engineering block: retro action item review, Atlas write-cutover decision
- 11:00 Architecture session: event pipeline roadmap
- 13:00 Lunch
- 14:00 Split sessions (on-call health, hiring, developer experience)
- 16:00 OKR finalization
- 18:00 Free evening

### Day 3 – Thursday 24 July

- 09:00 Decisions recap
- 10:00 Team charter refresh
- 11:30 Wrap-up, feedback round
- 12:30 Departure

## Key outcomes

### Strategy (from Claudia's talk)

- The company wants to "consolidate the platform and expand into adjacent markets" over the next 18 months. She was vague on details. Someone asked if that meant acquisitions. She said "we're always looking at options" and moved on quickly.
- Billing is called "core infrastructure" now. Positive in theory. In practice it means less room for experiments.
- Headcount for engineering is flat for H2. No new hires on our team.

### Retro action items review

| Item | Owner | Status at offsite |
|---|---|---|
| Re-enable disabled tests + CI check | Tobias | Done, 7 tests re-enabled, 2 deleted |
| 85% commitment cap | me | Running since sprint 20, ratio 1.0 |
| Risk register at kickoff | Lena | Template exists, not used yet |
| Incident comms template | Jonas | Drafted, Finance reviewing |
| Spike before sizing schema work | team | Used twice, both helped |

Overall: 3 of 5 done, 2 in progress. Good enough.

### Decisions

1. **Atlas write cutover moves to Q4.** Target 100% of writes on the new pipeline by 15 November. Reason: holiday period in August plus the Platform dependency. Markus wanted end of Q3. The room disagreed. He gave in, visibly unhappy.
2. **Atlas reads are declared done.** We'll celebrate this properly. Small win, but the team needed it.
3. **On-call rotation goes from 1-week to 2-week shifts with a secondary.** Fewer handovers, less context loss.
4. **Q3 OKRs agreed.** Three objectives, nine key results. Full list in [[Quarterly OKRs]].
5. **Developer experience budget:** 10% of each sprint reserved for tooling and tech debt. First time this is official.
6. **Hiring freeze acknowledged.** We will not backfill when Felix's QA contract ends in October. Concerning.

## Hallway conversations worth noting

- Lena thinks the "adjacent markets" line means a company purchase. She noticed Claudia and the CFO leaving dinner early for a call.
- Tobias wants to move to the Platform team. He asked me not to mention it yet.
- Markus and I had a 20-minute walk on day 2. He said my offsite presentation was "fine but very defensive about the delays". I didn't think it was defensive, I thought it was accurate. Left it there.
- Priya and Jonas both said the 85% cap is the single best change this year.

## My personal reflections

- Felt good presenting the retro. Felt less good after Markus's comment.
- The lake walk was the best part. More honest conversations in 90 minutes than in a month of standups.
- I noticed I am the person people come to with process problems, but I'm not the one who gets credit for delivery. Need to think about that before my next 1:1.
- Sleep in the hotel was bad. Back was sore by day 3 from the conference chairs.

## Follow-ups

- [ ] Share decision log in the team channel by Monday 28 July (me)
- [ ] Book the Atlas reads celebration (Lena, team lunch, budget 25 EUR per person)
- [ ] Update Jira with the Q4 target for write cutover (me)
- [ ] Send feedback form results to Claudia's assistant (Jonas)
- [ ] Ask Markus for written expectations for Q3, given the comment on day 2 (me)
