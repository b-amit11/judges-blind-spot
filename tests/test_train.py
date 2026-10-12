"""Synthetic end-to-end run of blindspot.train.train and the artifact contract app.py reads."""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from blindspot import train as train_module
from blindspot.data import METRICS
from blindspot.predict import predict


def synthetic_rounds(n_dates: int = 40, fights_per_date: int = 6) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows = []
    for d in range(n_dates):
        date = (pd.Timestamp("2015-01-03") + pd.Timedelta(weeks=d)).strftime("%Y-%m-%d")
        for f in range(fights_per_date):
            for r in (1, 2, 3):
                row: dict[str, object] = {
                    "fight_id": f"{d}-{f}",
                    "date": date,
                    "round": r,
                    "fighter_a": f"A{d}-{f}",
                    "fighter_b": f"B{d}-{f}",
                }
                for side in "ab":
                    attempted = int(rng.integers(10, 80))
                    landed = int(rng.integers(0, attempted + 1))
                    row.update(
                        {
                            f"{side}_sig_attempted": attempted,
                            f"{side}_sig_landed": landed,
                            f"{side}_head_landed": int(rng.integers(0, landed + 1)),
                            f"{side}_knockdowns": int(rng.integers(0, 2)),
                            f"{side}_takedowns": int(rng.integers(0, 4)),
                            f"{side}_sub_attempts": int(rng.integers(0, 2)),
                            f"{side}_control_seconds": int(rng.integers(0, 200)),
                        }
                    )
                gap = abs(int(row["a_sig_landed"]) - int(row["b_sig_landed"]))
                row["target"] = int(rng.random() < (0.45 if gap < 8 else 0.1))
                rows.append(row)
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def trained(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("root")
    (root / "data/processed").mkdir(parents=True)
    (root / "reports").mkdir()
    synthetic_rounds().to_csv(root / "data/processed/rounds.csv", index=False)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(train_module, "ROOT", root)
        train_module.train()
    return root


def test_report_contract_used_by_app(trained: Path) -> None:
    report = json.loads((trained / "reports/metrics.json").read_text())
    selected = report["selected_model"]
    assert set(report["test"]) == {"constant", "strike_gap", "logistic", "boosted_trees"}
    for key in ("average_precision", "brier", "precision_at_20"):
        assert 0 <= report["test"][selected][key] <= 1
    assert len(report["calibration"]["predicted"]) == len(report["calibration"]["observed"])
    assert {f["feature"] for f in report["feature_importance"]} >= {"sig_landed_gap", "round"}
    assert set(report["splits"]) == {"train", "validation", "test"}
    assert set(report["bootstrap_95pct"]) == {
        "brier",
        "average_precision",
        "brier_improvement_vs_closeness",
    }


def test_selection_uses_validation_brier_only(trained: Path) -> None:
    report = json.loads((trained / "reports/metrics.json").read_text())
    best = min(report["validation"], key=lambda n: report["validation"][n]["brier"])
    assert report["selected_model"] == best


def test_splits_are_chronological(trained: Path) -> None:
    splits = json.loads((trained / "reports/metrics.json").read_text())["splits"]
    assert splits["train"]["end"] < splits["validation"]["start"]
    assert splits["validation"]["end"] < splits["test"]["start"]


def test_saved_bundle_reproduces_saved_predictions(trained: Path) -> None:
    bundle = joblib.load(trained / "artifacts/model.joblib")
    assert set(bundle) == {"model", "name", "features", "limits"}
    saved = pd.read_csv(trained / "reports/test_predictions.csv")
    probability, notices = predict(bundle, saved)
    np.testing.assert_allclose(probability, saved.probability, atol=1e-12)
    assert len(notices) == len(saved)
    assert all(f"a_{m}" in saved for m in METRICS)
