# Critical review of this MVP

This is an assessment of the artifact, not an actual hiring decision. A beginner who can explain and improve it demonstrates more than someone who merely presents the generated code.

## What provides a hiring signal

The target is precise; the data join rejects ambiguous cases; symmetric inputs prevent arbitrary fighter-order behavior; preprocessing is fit on training only; chronological validation and simple baselines make the experiment credible. A functioning app, saved inference path, meaningful tests and honest failure cases show execution beyond a notebook.

The label source checks matter more than UI polish. A parser-ordering problem was identified and corrected rather than accepting a biased subset. Twenty rounds from four targeted fights were checked against the source scorecard pages.

## What does not yet provide a strong signal

- There is no measured user benefit or external user feedback.
- Data ends in June 2023. There is no evidence of present-day generalization.
- The dataset source has an unresolved redistribution license; the local demo is not a publicly launched product.
- This is not a novel ML algorithm. Similar MMA scoring models already exist. The narrower disagreement-review workflow is the project angle, not a priority claim.
- The model is small and training is straightforward. A Dockerfile does not establish production experience; its build has not been verified here.
- The candidate has not yet demonstrated independent understanding merely because this implementation exists.

## Critique of the ML results

Boosted trees improved Brier over the strike-gap baseline by approximately 0.0091 on the test set. The reported paired fight-bootstrap interval is positive, but it omits event clustering and selection uncertainty. Logistic regression achieved slightly better test Brier and average precision. Added model complexity has not established a clear advantage over full logistic regression.

The top-20 result is useful for a demo but is only 20 rounds, selected across the entire test period. It does not establish precision per event or save a measured amount of review time. The app’s ranked queue should be described as retrospective prioritization.

The 10 largest absolute errors are all low-probability misses of disagreement. Examples: Evloev–Lopes R3 (2.7% predicted), Font–Aldo R3 (3.0%), and Muhammad–Burns R5 (4.2%). The system should not be trusted to clear all contentious rounds. These are observed errors; no causal explanation is established from statistics alone.

Bootstrap uncertainty is uncertainty in aggregate metrics, not a confidence interval for any individual round. Training-range warnings are simple input checks, not a validated uncertainty or drift detector.

## My hiring-style verdict

**Credible beginner portfolio MVP; insufficient on its own for a big-tech MLE role.** I would use it to ask technical questions. If the candidate can explain the target, joins, leakage controls, metrics, failure modes and their own contributions, it is a useful conversation starter. If they cannot, the sophisticated-looking repository becomes a liability.

The best next improvement before September 30 is candidate understanding. Afterward: data rights and quality, a genuinely untouched recent test period, evaluation with real users, and then deployment reliability.
