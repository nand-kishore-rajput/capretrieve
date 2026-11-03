---
tags: [work, okrs, goals]
date: 2025-09-26
---

# Quarterly OKRs

Q3 2025 OKRs for the Billing team (July to September). Drafted and agreed at [[Team Offsite 2025]], refined in the first week of August. I'm the owner of KR 1.2 and KR 2.1 and co-owner on 3.3. Progress updated every other Friday. #okrs #goals

Scoring: 0.0 to 1.0. We aim for 0.7 as "good". 1.0 every time means the goals were too easy.

## Objective 1: Finish the Atlas migration safely

| KR | Description | Target | Current | Score |
|---|---|---|---|---|
| 1.1 | Write traffic on new pipeline | 50% | 40% | 0.8 |
| 1.2 | Zero Sev-1/Sev-2 incidents caused by Atlas | 0 | 0 | 1.0 |
| 1.3 | Decommission 3 legacy billing cron jobs | 3 | 2 | 0.67 |

**Notes:**
- 1.1 was 20% at end of July, 30% mid-August, 40% on 19 Sep. The final push to 50% depends on the Platform team upgrading the Kafka cluster, now scheduled for 6 October. So this will land in Q4.
- 1.2 is the one I'm proudest of. After the May Sev-2 we put so much into idempotency and testing. Zero incidents across the whole quarter.
- 1.3: the third cron job (monthly dunning letters) has a hidden dependency in the Support team's tooling. Found it on 9 Sep.

## Objective 2: Make the platform easier to build on

| KR | Description | Target | Current | Score |
|---|---|---|---|---|
| 2.1 | Integration-ready event APIs, documented and versioned | 4 event types | 3 | 0.75 |
| 2.2 | Onboarding time for a new engineer to first deploy | < 3 days | 4 days | 0.6 |
| 2.3 | 10% sprint capacity for dev experience, actually used | 10% | 8% | 0.8 |

**Notes:**
- 2.1 is officially about "internal and external consumers". The real driver is the integration work for [[Project Falcon]], which I can't mention to the team. Three of four event types are documented with schemas in the registry. The fourth (invoice voided) is waiting on a Finance decision.
- 2.2: we measured with Tobias's replacement candidate's trial day, plus a contractor in August. Biggest bottleneck: access requests take 1.5 days.
- 2.3: honestly decent. Things we did with that time: faster CI (from 19 to 11 minutes), local docker-compose setup that actually works, removed 2,400 lines of dead code.

## Objective 3: Healthier team operations

| KR | Description | Target | Current | Score |
|---|---|---|---|---|
| 3.1 | Sprint commit-to-done ratio | ≥ 0.9 | 0.94 avg | 1.0 |
| 3.2 | Pages outside working hours per on-call week | ≤ 2 | 2.5 | 0.8 |
| 3.3 | Team health survey "sustainable pace" score | ≥ 3.8 / 5 | 3.9 | 1.0 |

**Notes:**
- 3.1 is directly from the 85% cap. Sprints 20 to 25: 1.0, 0.95, 0.9, 0.92, 0.95, 0.9.
- 3.2 is better than Q2 (4.1) but not there yet. The noisy alert is the reconciliation lag check. Jonas has a fix ready.
- 3.3 went from 3.1 in Q2 to 3.9. Highest score in the whole department.

## Overall Q3 score

- Objective 1: 0.82
- Objective 2: 0.72
- Objective 3: 0.93
- **Team average: 0.82**

By our own rules that is a good quarter. Possibly too good on objective 3, which means we should stretch more there in Q4.

## How leadership sees it

From the review on 24 Sep with Markus and Claudia:

- Claudia: positive overall, especially 1.2 and 2.1. Said 2.1 is "strategically very important right now" and looked at me. Everyone else in the room missed it.
- Markus focused on 1.1 missing its target and said the team "could have pushed harder". Also mentioned my individual ticket count is low compared to Q1. I pointed out I own KR 1.2 and 2.1, which are both basically on target, and that I spent 2 weeks on a confidential DD project he himself assigned me to. He said "that's a separate topic".
- The contrast between the two of them was noticeable.

## Draft Q4 ideas

- **O1:** Complete Atlas. 100% writes on new pipeline by 15 Nov, decommission legacy billing by 15 Dec.
- **O2:** Integration readiness for an "external partner" (Falcon, if it signs). Possibly a sandbox environment.
- **O3:** Keep the team healthy through the QA contract ending and a likely departure (Tobias).
- Raise the bar on 3.1: shift from ratio to predictability, i.e. forecast accuracy within ±10%.

## Personal reflection

The team had its best quarter in a year by every measure we defined together. My own two KRs are at 1.0 and 0.75. And yet the message I keep getting in 1:1s is that I'm underperforming. The OKR numbers and the feedback don't match. I'm saving this table as evidence in case I need it later.
