---
tags: [work, process, agile]
date: 2025-07-11
---

# Sprint Planning

My working notes on how our team does sprint planning, what I changed after taking over as facilitator in sprint 12, and what still doesn't work. Started this note after the Q2 retro made it clear that planning was one of our biggest problems. See [[Project Retrospective]] for the full context. #process #agile

## Current setup (as of sprint 20)

- **Sprint length:** 2 weeks, Monday to Friday of the following week
- **Planning slot:** Monday 10:00 to 11:30 (hard stop, used to run until 12:30)
- **Who attends:** all 5 engineers, PM (Sandra, shared with the Payments team), QA (Felix, half-time)
- **Board:** Jira, one board for Atlas, one for maintenance and on-call work
- **Capacity sheet:** a small spreadsheet I fill in on Friday before planning (vacation days, on-call, public holidays in Bavaria vs Baden-Württemberg since two people commute from different states)

## The agenda I use now

1. **5 min:** Recap last sprint. Committed vs done, carried-over tickets, anything that blocked us.
2. **10 min:** Capacity check. Read out the number from the spreadsheet. Example from sprint 20: 5 people x 9 working days = 45 person-days, minus 4 vacation, minus 4.5 on-call, minus 3 for the offsite = 33.5 days.
3. **15 min:** PM walks through the top of the backlog. Only tickets that already meet the Definition of Ready.
4. **40 min:** Sizing and commitment. Planning poker for anything not yet sized.
5. **10 min:** Sprint goal, written as one sentence, pasted into the team channel.
6. **10 min:** Buffer. Usually eaten by one ticket nobody understands.

## Rules we agreed on

- **Commitment cap:** at most 85% of trailing 3-sprint average velocity. For sprint 20 that was 0.85 x 23.7 = about 20 points. This came straight out of the retro.
- **Definition of Ready:** acceptance criteria written, dependencies named, designs linked, size below 8 points. Anything 13 or above gets split or spiked.
- **Spikes are timeboxed.** Max 2 days, output is a written summary and a size, not code.
- **No new tickets mid-sprint** unless it's a Sev-1 or Sev-2. Everything else goes to the next planning.
- **On-call person commits to 50% capacity**, not 100%. Took a while to get Markus to agree to this.

## Velocity history

| Sprint | Committed | Done | Ratio |
|---|---|---|---|
| 14 | 34 | 22 | 0.65 |
| 15 | 32 | 25 | 0.78 |
| 16 | 35 | 21 | 0.60 |
| 17 | 30 | 26 | 0.87 |
| 18 | 28 | 24 | 0.86 |
| 19 | 26 | 23 | 0.88 |
| 20 | 20 | 20 | 1.00 |

Sprint 20 was the first time we completed everything we committed to. The team mood at the sprint review was noticeably different. Jonas said it was the first sprint in months where he did not feel behind on Wednesday.

## What still doesn't work

- **Estimation itself.** The cap protects us from overcommitting, but the individual estimates are still bad. Schema and migration work is consistently undersized by 2 to 3x. I keep a list of the worst ones in [[Estimation Mistakes]].
- **The PM is spread thin.** Sandra splits her week between us and Payments. Tickets often arrive at planning without acceptance criteria, so we write them live, which wastes 20 minutes.
- **Remote participants.** Priya joins from Leipzig on Mondays. Planning poker in the room with cards plus one person on video is awkward. Switched to a browser tool so everyone votes at the same time.
- **Hidden work.** Code reviews, incident follow-ups, interviewing candidates. None of this shows up on the board. I estimated in sprint 19 that about 18% of our time goes into stuff that isn't ticketed.

## Experiments to try

- [ ] **Backlog refinement on Thursday**, 45 minutes, so tickets are ready before Monday. Trial for sprints 21 to 23.
- [ ] **Track unplanned work** with a label "unplanned" and count it at the end of each sprint.
- [ ] **Reference stories.** Pick 3 completed tickets as anchors for 2, 5 and 8 points and show them at every poker round.
- [ ] **Rotate the facilitator.** I've run planning for 9 sprints. Partly for fairness, partly because it takes about 3 hours of my week including prep.
- [x] Hard stop at 11:30. Done since sprint 18, works fine.

## Dated notes

**2025-06-02** – Planning ran 2h40m. Committed 26 points. Two tickets had no acceptance criteria at all. I need to push back harder on this.

**2025-06-16** – Tried the capacity spreadsheet for the first time. People were surprised how few days we actually have once on-call and holidays come out. Good conversation.

**2025-06-30** – Markus asked why we were "only" committing 20 points. Explained the cap and the ratio table. He accepted it but said leadership looks at raw throughput. Noted.

**2025-07-14** – Sprint 20 planning, 1h25m. Under the hard stop for the first time. Sprint goal: "Write path for EU tenants runs on the new pipeline behind a flag at 10%."

## Things I've learned

- Planning is not a meeting about the backlog. It's a meeting about capacity and focus.
- A smaller, honest commitment builds more trust than a big one that slips.
- If the facilitator is also the person most behind on their own tickets (me, Q2), the meeting suffers. Prep needs protected time.
