# Agile Estimation: Story Points, Planning Poker, #NoEstimates and the Planning Fallacy

Estimation is one of the most debated practices in software development. Teams estimate work to plan releases, make trade-offs, coordinate with other teams and communicate with stakeholders. Software estimates are also notoriously inaccurate, and some practitioners argue that the effort spent producing them is often wasted. Agile methods introduced relative estimation techniques such as story points and planning poker, and later the #NoEstimates movement questioned whether detailed estimation is needed at all. This article describes these approaches, the psychological biases that affect estimates, and what is known about estimation accuracy.

## Why Teams Estimate

Estimates serve several purposes, and confusing them causes trouble:

- **Forecasting:** answering "when will it be done?" or "how much can we deliver by a date?"
- **Prioritisation:** comparing the cost of items against their expected value.
- **Shared understanding:** discussing an estimate often exposes different assumptions about scope, risk or technical approach.
- **Commitment and capacity planning:** deciding how much work to take into an iteration.

A recurring problem is that a forecast, which is a probabilistic statement, gets treated as a commitment or deadline. This creates pressure to pad estimates or to cut quality to meet them.

## Story Points

Story points are a unit of **relative** estimation. Instead of estimating in hours or days, teams compare work items with each other. A story estimated at 5 points is expected to take more effort than one at 2 points. Points are meant to capture effort, complexity and uncertainty together.

Common characteristics include:

- **Non-linear scales.** Many teams use a modified Fibonacci sequence (1, 2, 3, 5, 8, 13, 20, 40, 100) or "T-shirt sizes" (XS to XL). The widening gaps reflect greater uncertainty for larger items.
- **Reference stories.** Teams pick a few completed items as anchors for comparison.
- **Velocity.** Over time, the number of points a team completes per iteration becomes its velocity, which is used for forecasting.

Proponents argue that people are better at comparing sizes than at estimating absolute durations, and that points separate estimation from individual working speed. Critics point out several problems. Points are often converted back into time implicitly. Velocity becomes a performance target and invites "point inflation." Points cannot be compared across teams. And the abstraction can confuse stakeholders. Some originators of the practice have since said they regret how story points are commonly misused.

## Planning Poker

Planning poker is a consensus-based estimation technique, derived from the Wideband Delphi method:

1. The product owner or another team member describes a backlog item.
2. The team discusses it briefly and asks clarifying questions.
3. Each estimator privately chooses a card with an estimate.
4. All cards are revealed at the same time.
5. If estimates differ widely, the people with the highest and lowest estimates explain their reasoning, and the team discusses and votes again.
6. The process repeats until the estimates converge or the team agrees on a value.

Revealing estimates at the same time is meant to reduce **anchoring**, where an early number skews later ones, and the influence of senior or dominant voices. Much of the value is often attributed to the discussion rather than the number. A wide spread of estimates can reveal hidden complexity or misunderstandings about requirements. Research on group estimation suggests that structured combination of independent estimates can improve accuracy over individual estimates, though results depend on context and the group's expertise.

Variations include affinity estimation, where items are quickly sorted into size buckets, and "bucket system" methods for estimating large backlogs efficiently.

## The #NoEstimates Movement

#NoEstimates began as a social media hashtag and grew into a loose movement that questions the value of traditional estimation. Its ideas are not a single method, but common themes include:

- **Slice work small.** If items are broken down into similarly small pieces, counting items completed per unit of time (throughput) can forecast as well as estimating each item.
- **Use historical data.** Probabilistic forecasting techniques, such as Monte Carlo simulation based on past throughput or cycle times, can produce date ranges with confidence levels, for example "85 percent likely by a given date."
- **Focus on value and feedback.** Delivering early and often, then adjusting based on feedback, reduces the need for long-range predictions.
- **Question the purpose.** If an estimate will not change a decision, the effort to produce it may be waste.

Critics respond that many organisational contexts, such as contracts, budgets, regulatory deadlines and dependencies, genuinely need some form of estimate. They also point out that breaking work into small slices itself needs judgement similar to estimation, and that "no estimates" can be misunderstood as "no planning." Many practitioners take a middle path: lightweight estimation or counting combined with frequent re-forecasting.

## The Planning Fallacy and Cognitive Biases

The **planning fallacy**, a term from research on judgement and decision-making, describes the tendency to underestimate how long one's own tasks will take, even when similar past tasks overran. Contributing factors include:

- **Optimism bias:** imagining the best-case path and overlooking possible obstacles.
- **Focus on the specific case (the "inside view"):** reasoning about the details of the current task rather than how similar tasks turned out.
- **Anchoring:** being swayed by an initial number, such as a stakeholder's desired deadline.
- **Motivational pressures:** wanting to please stakeholders or win approval for a project.
- **Unknown unknowns:** work that is only discovered during implementation.

A widely recommended remedy is **reference class forecasting**, also called taking the "outside view." This means basing estimates on the actual outcomes of a set of comparable past projects, then adjusting for specific differences. Breaking work into smaller parts can help but can also miss integration work and overhead. Asking people to give ranges or confidence intervals tends to show that they are overconfident, with stated ranges that are too narrow.

## Estimation Accuracy

Studies of software projects consistently find that overruns of effort and schedule are common, although reported averages vary widely depending on the definitions and samples used. Some observations recur across studies:

- **The cone of uncertainty.** Estimates made early, when requirements are vague, have much wider error ranges than those made later. The exact numbers often quoted for the cone are illustrative rather than precisely measured.
- **Expert judgement versus models.** Formal estimation models do not consistently outperform expert judgement. Combining several methods or estimators can improve accuracy.
- **Feedback improves calibration.** Teams that track actual results against estimates and review the gap tend to improve over time.
- **Irrelevant information biases estimates.** Experiments show that anchors, such as a client's suggested figure, influence estimates even when the estimators know the anchor is irrelevant.

Estimation accuracy also depends on what is measured. Comparing against the original scope is often unfair, because scope usually changes during a project.

## Practical Guidance

Common recommendations across these schools of thought include:

- be explicit about whether a number is a forecast, a target or a commitment;
- express forecasts as ranges with confidence levels;
- use historical data where possible;
- keep work items small and re-forecast frequently;
- treat estimation discussions as a tool for finding risks and building shared understanding;
- avoid using velocity or points as performance metrics for individuals or teams.

## Summary

Agile estimation techniques such as story points and planning poker aim to make estimation faster and more collaborative through relative sizing and structured discussion. The #NoEstimates movement argues that small slices and throughput-based forecasting can replace much detailed estimation. Cognitive biases, especially the planning fallacy, make underestimation common, and reference class forecasting and historical data are the most widely recommended correctives. No method eliminates uncertainty. Expressing estimates as ranges and updating them frequently is broadly regarded as good practice.
