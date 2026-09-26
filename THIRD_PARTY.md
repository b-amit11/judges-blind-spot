# Data provenance and distribution status

This project contains new pipeline and app code. It does not claim authorship of the input datasets or of previous MMA scoring work.

## Round data

Repository: https://github.com/DylanBaut/MMA_Data_Analysis

Pinned commit: `aa04256dd35102c0d489b62ed13b58e04a5c471f`

Files: `UFC.csv` (round statistics), `decisions.csv` (individual judge margins). The upstream scraper code was read to understand field semantics; it was not incorporated into this implementation. Underlying sources are UFCStats and MMA Decisions.

No explicit reuse license was found in the inspected repository snapshot. Local copies support this research prototype; no raw/derived dataset or model is published by this task. Public availability is not a grant of redistribution rights. Before hosting the historical rows publicly or distributing a data/model package, clarify permissions or substitute a clearly licensed source.

## Metadata

Repository: https://github.com/komaksym/UFC-DataLab

Pinned commit: `3268146c05211de9deab8b9b4c0bb4a954815f0b`

File: `data/merged_stats_n_scorecards/merged_stats_n_scorecards.csv`.

Repository license: MIT, copyright (c) 2024 komaksym. See `licenses/UFC-DataLab-MIT.txt`. A repository license does not independently resolve every underlying provider's rights.

## Publication packaging

`.gitignore` excludes raw data, processed data, row-level reports and fitted joblib artifacts. Source code, aggregate evaluation reports and documentation can be prepared separately from downloaded data. The ignored local files remain available for the working demo. A future deployment needs an explicit data-distribution decision, a hosting destination, and an actual deployment check.
