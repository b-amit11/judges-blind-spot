# Judge’s Blind Spot

**Which MMA rounds are likely to divide the judges?** A working post-round review tool, built with Python, scikit-learn and Streamlit. It estimates disagreement among three judges, not the correct winner or the likelihood of corruption.

Status: **working local research MVP**. Real-data pipeline, four-model comparison, trained artifact, interactive demo, automated tests, and source audit. No public deployment or GitHub remote has been created. Docker and CI definitions are provided; Docker has not been run and remote CI has not executed.

## Start here

Read [START_HERE.md](START_HERE.md) for the beginner walkthrough, demo script and September 30 preparation plan. On the original computer, double-click `Start Demo.command` or open http://127.0.0.1:8501 while the server is running.

On another machine (Python 3.12+):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lock.txt
python -m blindspot.data
python -m blindspot.train
python -m pytest -q
streamlit run app.py
```

The data command downloads three pinned public CSVs. Internet access is needed initially. After training, the demo works locally without downloading data again. `requirements-lock.txt` records the actual tested Python 3.14 environment; other Python/platform combinations may need `requirements.txt` and retraining. Never load an untrusted joblib/pickle artifact.

## Actual benchmark

6,439 rounds from 2,065 uniquely matched fights, March 2009–June 2023. Inputs come only from the round being evaluated. Target = judges disagree on the round winner; a tied score is a distinct outcome. Judges giving 10–9 and 10–8 to the same fighter still agree on the winner.

| Split | Rounds | Fights | Dates |
|---|---:|---:|---|
| Training | 4,281 | 1,387 | 2009-03-07 to 2020-03-07 |
| Validation | 1,057 | 331 | 2020-03-14 to 2021-10-16 |
| Test | 1,101 | 347 | 2021-10-23 to 2023-06-17 |

| Model | Test average precision ↑ | Test Brier ↓ | Precision@20 ↑ |
|---|---:|---:|---:|
| Constant training prevalence | 0.219 | 0.1712 | 0.25* |
| Significant-strike gap logistic baseline | 0.276 | 0.1666 | 0.25 |
| Full logistic regression | **0.381** | **0.1564** | 0.50 |
| Boosted trees, selected on validation | 0.371 | 0.1575 | 0.50 |

*A constant predictor cannot rank rounds; its top-20 score depends on tie order and is not meaningful ranking evidence.*

Boosted trees had the lowest **validation** Brier (0.1424 vs logistic 0.1463). The selected model was retained even though logistic performed slightly better on test. No claim that trees are universally superior. The selected model's top 20 contained 10 disagreement rounds; overall test prevalence was 21.9%. This is an offline result, not evidence of real analyst time saved.

Fight-clustered bootstrap 95% intervals (400 samples): selected-model average precision 0.321–0.434; Brier 0.1466–0.1703; Brier improvement over the strike-gap model 0.0035–0.0148. These conditional intervals do not capture model-selection uncertainty, shared-event effects or source errors. Twenty selected rounds is a small sample.

Metrics are recorded in `reports/metrics.json`. Average precision summarizes the precision-recall curve; it is not accuracy and is not trapezoidal PR-AUC. A 50% Precision@20 does not mean 50% overall accuracy.

## Data engineering and leakage controls

1. Download commit-pinned raw sources; record SHA-256 hashes.
2. Normalize fighter names and join only pairs unique in all three sources. Reject rematches rather than fuzzy-match them.
3. Reconstruct each judge’s full totals from round margins. Reject inconsistencies, known deductions and nonstandard decisions.
4. Cross-check the three unordered total-score pairs against a separate UFCStats export. UFCStats detail scores do not reliably follow corner order. Named score rows establish orientation.
5. Verify each fighter’s summed significant strikes against the independent metadata table.
6. Derive 17 symmetric numeric features: gaps and totals for seven statistics, accuracy gap, striking/takedown directional conflict, and round number.
7. Split chronologically by event date, keeping whole fights and dates together. Fit imputation/scaling only on training data.

No model inputs include fighter name, judge identity, scorecards, fight outcome, weight-class metadata, or later rounds. Weight class is retained as metadata only. Model comparison has fixed small configurations, with no broad parameter search.

An early debugging run exposed a source-ordering assumption that unnecessarily excluded 1,219 fights. It was corrected by inspecting the source parser and score pairs, not by optimizing test performance. The benchmark was regenerated with unchanged model configurations. This is a development holdout, not a pristine prospective evaluation. Future model improvements should use a new, untouched period.

## Product and engineering

- Ranked held-out review queue; fighter search; optional score reveal.
- Hypothetical round sandbox with input validation and training-range notices.
- Calibration plot, baseline table, global feature importance and limitations.
- Serialized model and preprocessing; shared feature and inference code.
- Tests for target semantics, time parsing, symmetry, leakage, temporal isolation, saved inference and app interactions.
- Reproducible commands, source manifest, audit report and model/data checksums.

`blindspot/data.py` builds data; `features.py` defines inputs; `train.py` compares models; `predict.py` validates inference; `app.py` is the UI. Reports include the 10 largest prediction errors and a random 20-row audit worksheet.

Local warm feature+inference timing was about 5.5 ms median / 7.8 ms p95 over 50 calls. This excludes UI/network and is not a production latency guarantee.

## Sources and limitations

- Round stats and judge margins: [DylanBaut/MMA_Data_Analysis](https://github.com/DylanBaut/MMA_Data_Analysis), from UFCStats and MMA Decisions. Data snapshot ends June 2023. No explicit reuse license was found in the inspected repository snapshot; public accessibility does not establish redistribution permission.
- Dates and aggregate checks: [komaksym/UFC-DataLab](https://github.com/komaksym/UFC-DataLab), MIT-licensed repository. Its newer metadata does not make the round dataset current.
- See [THIRD_PARTY.md](THIRD_PARTY.md) before distributing source data or publishing a data-bearing demo. Raw and derived tables and fitted model files are excluded from Git by default.

This is a selected subset of decision fights. Excluding ambiguous names, rematches, point deductions and broken records can bias results. Aggregate counts cannot fully represent effective damage, timing or submission danger. A 20-round source check supports ingestion correctness for that small targeted sample; it is not a full independent audit against commission originals. Current UFC generalization and user usefulness remain untested.

## After the career fair

Obtain clearly licensed current round data; reserve an untouched test period; audit commission scorecard originals; measure review usefulness with analysts; compare event-clustered intervals and weight-class slices; study calibration; then consider serving/monitoring infrastructure. Public deployment awaits a clear data-distribution basis and a hosting destination.
