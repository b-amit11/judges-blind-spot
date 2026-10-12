"""Input validation and range notices in blindspot.predict, without a trained artifact."""

from typing import Any

import numpy as np
import pandas as pd
import pytest

from blindspot.data import METRICS
from blindspot.features import features
from blindspot.predict import predict

ROUND = {
    "sig_attempted": 40,
    "sig_landed": 20,
    "knockdowns": 0,
    "takedowns": 1,
    "sub_attempts": 0,
    "control_seconds": 30,
    "head_landed": 15,
}


class FixedModel:
    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        return np.tile([0.7, 0.3], (len(x), 1))


def make_round(**changes: Any) -> pd.DataFrame:
    row: dict[str, Any] = {"round": 2, **{f"{s}_{m}": v for s in "ab" for m, v in ROUND.items()}}
    row.update(changes)
    return pd.DataFrame([row])


@pytest.fixture
def bundle() -> dict[str, Any]:
    x = features(pd.concat([make_round(), make_round(a_sig_landed=30, round=1)]))
    limits = {c: {"min": float(x[c].min()), "max": float(x[c].max())} for c in x}
    return {"model": FixedModel(), "limits": limits}


def test_in_range_round_has_no_notices(bundle: dict[str, Any]) -> None:
    probability, notices = predict(bundle, make_round())
    assert probability.tolist() == [0.3]
    assert notices == [{"missing_features": [], "outside_training_range": []}]


def test_out_of_range_and_missing_features_are_reported(bundle: dict[str, Any]) -> None:
    _, notices = predict(
        bundle, make_round(a_takedowns=9, a_sig_attempted=0, a_sig_landed=0, a_head_landed=0)
    )
    assert "takedowns_gap" in notices[0]["outside_training_range"]
    assert notices[0]["missing_features"] == ["accuracy_gap"]


@pytest.mark.parametrize(
    "changes,message",
    [
        ({"round": 6}, "Round must be between one and five"),
        ({"a_control_seconds": 301}, "Control cannot exceed 300 seconds"),
        ({"a_takedowns": -1}, "nonnegative finite"),
        ({"b_knockdowns": np.inf}, "nonnegative finite"),
        ({"a_sig_landed": 20.5}, "whole numbers"),
        ({"a_sig_landed": 41}, "Landed strikes cannot exceed attempts"),
        ({"b_head_landed": 21}, "head strikes cannot exceed"),
    ],
)
def test_invalid_inputs_rejected(
    bundle: dict[str, Any], changes: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        predict(bundle, make_round(**changes))


def test_missing_column_rejected(bundle: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="Missing required round statistics"):
        predict(bundle, make_round().drop(columns=[f"a_{next(iter(METRICS))}"]))
