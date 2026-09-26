# Ten largest held-out errors

Selected by absolute probability error, not manually chosen examples. All ten are false negatives at a 0.5 threshold. These data describe errors; they do not establish the causal reason for each miss.

| Fight | Round | Predicted disagreement | Observed disagreement | Significant strikes A–B | Control seconds A–B |
|---|---:|---:|---|---:|---:|
| Movsar Evloev vs Diego Lopes | 3 | 2.7% | Yes | 33–10 | 156–16 |
| Rob Font vs Jose Aldo | 3 | 3.0% | Yes | 37–12 | 0–130 |
| Rob Font vs Marlon Vera | 2 | 4.0% | Yes | 51–27 | 0–23 |
| Belal Muhammad vs Gilbert Burns | 5 | 4.2% | Yes | 42–21 | 0–0 |
| Kai Kara-France vs Amir Albazi | 4 | 4.5% | Yes | 27–5 | 11–23 |
| Jeremiah Wells vs Matthew Semelsberger | 2 | 5.7% | Yes | 16–6 | 189–30 |
| Julio Arce vs Daniel Santos | 1 | 6.4% | Yes | 39–17 | 0–35 |
| Dustin Jacoby vs John Allan | 3 | 6.9% | Yes | 48–27 | 0–0 |
| Martin Buday vs Lukasz Brzeski | 2 | 7.2% | Yes | 19–43 | 0–0 |
| Tim Means vs Max Griffin | 3 | 7.6% | Yes | 10–4 | 61–224 |

Pattern: many misses have a large strike-count gap. The model often associates such gaps with agreement, but some judges still disagree. Missing context and source noise remain plausible; footage review would be required to attribute causes.

The full logistic model slightly outperformed the selected tree model on final-test Brier and average precision. No post-test model switch was made. Source scorecards for four of these fights were spot-checked; see SOURCE_CHECK.md.
