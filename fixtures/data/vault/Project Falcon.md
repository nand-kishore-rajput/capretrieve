---
tags: [work, confidential, acquisition, falcon]
date: 2025-08-19
---

# Project Falcon

> **CONFIDENTIAL. Do not share, do not forward, do not discuss outside the named group.** I'm only writing this down here because I need to keep track of my technical due-diligence tasks and dates. Nothing in this note may reach the press, customers, or anyone not on the list below. #confidential

## What it is

"Falcon" is the internal code name for the acquisition of **Nordwerk Data GmbH**, a ~45-person company in Hamburg that builds invoice-matching and reconciliation software for mid-sized logistics companies. They have a strong ML-based matching engine and about 220 paying customers, mostly in DACH and the Netherlands.

The code name is used everywhere: in calendar invites, in the data room, in file names. Never write "Nordwerk" in Slack, Jira or email subjects. Calendar entries just say "Falcon sync".

## The deal

- **Agreed price: 40 million EUR** (enterprise value), signed term sheet on 8 August 2025
- Structure: roughly 70% cash at closing, 30% earn-out over 24 months tied to ARR targets
- Earn-out milestone 1: Nordwerk ARR reaches 9.5 million EUR by end of 2026
- Key-person retention packages for their CTO and two lead engineers (3-year vesting)
- Their brand stays for at least 12 months, then gets folded into our billing product
- Exclusivity period: 60 days from term sheet, so until 7 October 2025

This finally explains Claudia's "adjacent markets" line at the offsite. The plan is to plug their matching engine into our billing pipeline. That means the event pipeline from Atlas becomes the integration point. Which is presumably why I got pulled in.

## Who is in the loop

Strictly limited. Everyone signed an additional NDA on 11 August.

- **Claudia Rehm** – Director of Engineering, technical sponsor
- **CFO** (Henrik Asmussen) – deal owner, leads negotiations
- **General Counsel** (Dr. Petra Lindqvist) and the external law firm
- **Head of Corporate Development** (Yusuf Demir)
- **Markus Brenner** – my manager, for team capacity planning
- **Me** – technical due diligence on their data pipeline, APIs and integration effort
- **Sophie Klein** – security lead, for the security and GDPR review
- On their side: CEO, CTO, CFO only

Not in the loop: the rest of my team, including Lena, Tobias, Priya and Jonas. When they ask why I'm in so many "Falcon syncs" I say it's a platform architecture review. I hate this, but those are the rules.

## Due-diligence timeline

| Date | Milestone | Owner |
|---|---|---|
| 8 Aug | Term sheet signed | CFO |
| 11 Aug | NDAs signed, data room opened | Legal |
| 18 to 29 Aug | Technical DD: architecture, code quality, infra costs | me, Sophie |
| 25 Aug | On-site visit in Hamburg (one day) | Claudia, me |
| 1 to 12 Sep | Financial and legal DD | CFO, Legal |
| 15 Sep | DD findings report to the board | Yusuf |
| 22 Sep | Final price confirmation or renegotiation | CFO |
| 30 Sep | Target signing (SPA) | all |
| Q4 2025 | Closing, subject to antitrust clearance | Legal |

## My technical DD checklist

- [x] Architecture overview reviewed (monolith in Python, Postgres, some Go services)
- [x] Data room: API docs, infra diagrams, cost breakdown
- [ ] Code walkthrough with their CTO (scheduled 25 Aug in Hamburg)
- [ ] Estimate integration effort with our event pipeline
- [ ] Check licensing of their ML dependencies
- [ ] Infra costs: they spend about 38,000 EUR/month on cloud. Verify against usage numbers
- [ ] Single points of failure: one engineer seems to own the whole matching model. Flag as key-person risk
- [ ] Data protection: where is customer invoice data stored, who has access

## Early observations (19 Aug)

- Their matching engine is genuinely good. Claimed 94% auto-match rate, I'd like to see how it's measured.
- Test coverage is low, around 35% by their own report.
- Deployment is manual for two of their services. Not a deal-breaker, but integration will take longer than Corp Dev thinks.
- My rough integration estimate: 3 to 4 quarters with 4 engineers. Corp Dev's slide says "2 quarters". I've learned my lesson about optimistic numbers. I'll put my real number in the report.

## Leak rules (written down so I don't slip)

- Nothing about Falcon goes to the press. Any journalist contact goes straight to the comms lead, no comment from anyone else.
- No printouts. No screenshots of the data room (it's watermarked anyway).
- No Falcon discussion in open-plan areas or on the train.
- Don't use the personal laptop for data-room access.
- If it leaks, the deal can collapse and it may be a legal issue under insider rules, since our parent company has listed bonds.

## Connection to OKRs

Claudia asked that Falcon integration readiness get folded quietly into the platform objective without naming it. It shows up as a vague "integration-ready event APIs" key result in [[Quarterly OKRs]]. Most of the team will think it's about internal consumers.

## Personal note

Strange to be trusted with this while Markus keeps hinting my performance is slipping. If I'm good enough for a 40 million EUR due diligence, I'm good enough for my day job. Keeping that thought to myself for now.
