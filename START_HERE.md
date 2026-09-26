# Your first 45 minutes

You have a real local MVP. It was built with AI assistance. Your immediate job is to understand and inspect it, then make a small change yourself—not memorize claims you cannot defend.

## 1. Open the demo — 5 minutes

Double-click `Start Demo.command` in this folder. While the server is running, open http://127.0.0.1:8501. To stop the server, press Ctrl+C in its terminal. The current session may already be running it.

The first tab lists historical rounds ranked by estimated disagreement. Pick a round. Look at the statistics before revealing the judges. In the sandbox, change the two fighters' counts and recompute. Try making landed strikes exceed attempted strikes: the app should reject that input.

## 2. Understand one row — 10 minutes

One row is one round, with two fighters’ statistics and three judges’ scores. The model sees statistics but never the scores. The scores tell us whether its prediction was useful after the fact.

Imagine three judges pick A, A, B. The target is 1: disagreement. If they pick A, A, A, it is 0. If they all pick A but one gives 10–8 while the others give 10–9, it is still 0. The project studies winner disagreement, not score-margin disagreement.

A feature is an input number. “Significant-strike gap” means the absolute difference between the fighters’ landed significant strikes. Absolute gaps and totals preserve the prediction if we swap fighter A and B. We test that property.

## 3. Understand the experiment — 10 minutes

Training data teaches the model patterns. Validation data chooses between candidate models. Test data measures the already chosen model on later fights.

Splitting individual rounds randomly could put one round of a fight in training and another in test. Our chronological event-date split avoids that overlap and better resembles moving forward in time. It still does not prove performance on 2026 fights.

A baseline is a deliberately simple competitor. We used both a constant probability and a model with only the significant-strike gap. A complicated model should earn its complexity by improving on these.

Brier score measures probability error: the average of `(predicted_probability - actual_0_or_1)^2`. Lower is better. Average precision measures whether disagreement rounds appear high in the ranking. Higher is better. The test disagreement prevalence was 21.9%, which is the constant model's average precision.

## 4. Inspect an actual failure — 10 minutes

In the fighter filter, choose Rob Font. Find round 3 against Jose Aldo. The model estimated only about 3.0% disagreement, but the source scorecards show a dissenting judge. This is a confident miss. Font landed more significant strikes in that round; these counts alone did not capture the judging outcome.

Do not claim you know exactly why the model failed without watching footage and checking the labels. Possible explanations include missing fight context, limited features, noisy labels, or a pattern the model failed to learn.

## 5. Make one change you understand — 10 minutes

Open `app.py`. Change a help sentence and restart or refresh the app. Then read the `disagreement()` function in `blindspot/data.py` and the corresponding tests. Explain aloud why `[1,1,2]` gives 0 but `[1,1,-1]` gives 1.

Next, run `python -m pytest -q` in the activated environment. A passing test means that specific check passed; it does not prove the ML model is accurate.

## Career-fair plan

| Date | Priority | Finish condition |
|---|---|---|
| September 26 | Run the demo and understand target/features/splits | Explain the project without reading this file |
| September 27 | Trace one row through the code; make one small change; inspect failures | Explain a test, baseline, and failure |
| September 28 | Practice questions; prepare a source-code portfolio link if desired | Explain the results and limitations in two minutes |
| September 29 | Finalize resume; rehearse; keep a local demo ready | Deliver a clear 45-second pitch and answer follow-ups |
| September 30 | Show the demo and discuss learning honestly | Describe what you built, verified and still need to improve |

Avoid beginning three more projects before you can explain this one. For a beginner, four days of understanding and improving one working project is a better use of this deadline.

## Resume wording

Use only after you can walk through the implementation:

**Judge’s Blind Spot — MMA ML Research Prototype | Python, scikit-learn, Streamlit**

- Developed an AI-assisted MMA round-review prototype with a reproducible pipeline covering 6,439 rounds from 2,065 fights, temporal evaluation, and automated data and inference checks.
- Compared four models; the validation-selected model identified judge disagreement in 10 of the top 20 ranked test rounds, versus 21.9% test prevalence; implemented an interactive review and scenario-testing app.

Do not write “production ML,” “real-time UFC scoring,” “state of the art,” “deployed” or “expert-level Python.” None of those claims is established. If asked, say AI helped generate the implementation, and explain your own verification, modifications and learning.

## A 45-second pitch

“I’m learning ML engineering through an MMA project that predicts whether judges will disagree about a round. It uses completed-round statistics, so it’s for post-round review. I kept whole fights together and tested on later events to avoid leakage. The model found disagreement in 10 of its top 20 flagged test rounds, against about 22% overall. The interesting result is that boosted trees won on validation, but the simpler logistic model did slightly better on test. I kept that result visible. My next step is better-licensed current data and a fresh evaluation. I built it with AI assistance and am learning the pipeline end to end.”

## Questions you should be able to answer

1. What exactly is the target? Explain agreement on winner versus agreement on score margin.
2. When is a prediction made? After the round, with completed statistics.
3. Why not report only accuracy? Most rounds have agreement; an always-agreement classifier looks deceptively good.
4. What is leakage? Information that would not be available at prediction time, or contamination between evaluation and training.
5. Why no fighter names? They could encourage shortcuts, and the first version focuses on round activity.
6. Why not deep learning? A modest tabular dataset and useful simple baselines do not justify extra complexity yet.
7. Why keep trees if logistic did better on test? Test data should not become the selection set.
8. What is your worst limitation? Historical selected data and counts that cannot capture all judging context.
9. Did you save analysts time? Not measured; this is only an offline ranking result.
10. What did you personally do? Answer truthfully with what you have actually inspected, modified and verified.
