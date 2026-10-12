"""Synthetic-source tests for the join and rejection rules in blindspot.data.build."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from blindspot import data

# Judge margins per round, positive = Alpha One won the round.
# Round 1: all agree; round 2: judge C dissents; round 3: judge B dissents.
MARGINS = {"A": [1, 1, -1], "B": [1, 1, 1], "C": [1, -1, -1]}
FULL_SCORES = ["29", "28", "30", "27", "28", "29"]
ROUND_STATS = {
    "Sig_Strikes_Attempted": (30, 20),
    "Sig_Strikes_Landed": (10, 5),
    "KD": (0, 0),
    "TD": (1, 0),
    "Sub_Attempts": (0, 0),
    "Ctrl_Time": ("1:30", "0:00"),
    "Head_Strikes": (6, 3),
}


def sources() -> dict[str, dict[str, Any]]:
    score = {"Opponent_A": "Alpha One", "Opponent_B": "Beta Two", "Full_Scores": str(FULL_SCORES)}
    for judge, card in MARGINS.items():
        for r, margin in enumerate(card, start=1):
            score[f"Rd{r}{judge}"] = margin
    stat: dict[str, Any] = {
        "Opponent_A": "Alpha One",
        "Opponent_B": "Beta Two",
        "Number_of_Rounds": 3,
        "Decision1": "28 29",
        "Decision2": "27 30",
        "Decision3": "29 28",
    }
    for r in range(1, 4):
        for source, (a, b) in ROUND_STATS.items():
            stat[f"Round_{r}_{source}_(A)"] = a
            stat[f"Round_{r}_{source}_(B)"] = b
    meta = {
        "red_fighter_name": "ALPHA ONE",
        "blue_fighter_name": "BETA TWO",
        "method": "Decision - Split",
        "details": "Judge X 29 - 28. Judge Y 30 - 27. Judge Z 28 - 29.",
        "event_date": "07/03/2015",
        "event_name": "Synthetic Fight Night",
        "bout_type": "Lightweight Bout",
        "red_fighter_sig_str": "30 of 90",
        "blue_fighter_sig_str": "15 of 60",
    }
    return {"scores": score, "stats": stat, "metadata": meta}


def run_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rows: dict[str, Any]
) -> pd.DataFrame:
    raw = tmp_path / "data/raw"
    raw.mkdir(parents=True)
    for name in ("scores", "stats", "metadata"):
        value = rows[name]
        pd.DataFrame(value if isinstance(value, list) else [value]).to_csv(
            raw / f"{name}.csv", index=False
        )
    monkeypatch.setattr(data, "ROOT", tmp_path)
    return data.build()


def test_valid_fight_is_accepted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    frame = run_build(tmp_path, monkeypatch, sources())
    assert frame["round"].tolist() == [1, 2, 3]
    assert frame.target.tolist() == [0, 1, 1]
    assert frame.judge_3_margin.tolist() == MARGINS["C"]
    assert frame.date.unique().tolist() == ["2015-03-07"]
    assert frame.a_control_seconds.tolist() == [90, 90, 90]
    assert frame.fight_id.nunique() == 1
    audit = json.loads((tmp_path / "reports/data_audit.json").read_text())
    assert audit["accepted_fights"] == 1 and audit["rounds"] == 3 and audit["disagreements"] == 2
    assert (tmp_path / "data/processed/rounds.csv").exists()


def test_reversed_stat_corners_flip_margins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = sources()
    stat = rows["stats"]
    stat["Opponent_A"], stat["Opponent_B"] = "Beta Two", "Alpha One"
    for key in [k for k in stat if k.endswith("_(A)")]:
        other = key[:-3] + "(B)"
        stat[key], stat[other] = stat[other], stat[key]
    frame = run_build(tmp_path, monkeypatch, rows)
    assert frame.fighter_a.unique().tolist() == ["Beta Two"]
    assert frame.judge_3_margin.tolist() == [-m for m in MARGINS["C"]]
    assert frame.target.tolist() == [0, 1, 1]
    assert frame.b_sig_landed.sum() == 30


REJECTIONS: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
    ("Point deduction", lambda r: r["metadata"].update(details="Point deducted for groin strike")),
    ("Not a full standard decision", lambda r: r["metadata"].update(method="KO/TKO")),
    ("Not a full standard decision", lambda r: r["stats"].update(Number_of_Rounds=4)),
    (
        "Round scores do not reconstruct totals",
        lambda r: r["scores"].update(Full_Scores="['30', '27', '30', '27', '28', '29']"),
    ),
    ("Missing full scorecards", lambda r: r["scores"].update(Full_Scores="['29', '28']")),
    ("Invalid score", lambda r: r["scores"].update(Rd1A=4)),
    ("Scorecards disagree across sources", lambda r: r["stats"].update(Decision1="27 29")),
    ("Invalid strike counts", lambda r: r["stats"].update({"Round_1_Sig_Strikes_Landed_(A)": 31})),
    ("Aggregate strike mismatch", lambda r: r["metadata"].update(red_fighter_sig_str="31 of 90")),
    ("Invalid control time", lambda r: r["stats"].update({"Round_2_Ctrl_Time_(A)": "1:75"})),
    ("ambiguous_or_missing_pair", lambda r: r.update(scores=[r["scores"], dict(r["scores"])])),
    ("ambiguous_or_missing_pair", lambda r: r["metadata"].update(red_fighter_name="Someone Else")),
]


@pytest.mark.parametrize(
    "reason,change", REJECTIONS, ids=[f"{i}-{r}" for i, (r, _) in enumerate(REJECTIONS)]
)
def test_rejection_rules(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reason: str,
    change: Callable[[dict[str, Any]], None],
) -> None:
    rows = sources()
    change(rows)
    with pytest.raises(ValueError, match="No accepted data") as exc:
        run_build(tmp_path, monkeypatch, rows)
    assert reason in str(exc.value)


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_download_failure_names_the_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def offline(url: str, timeout: float) -> FakeResponse:
        raise OSError("network unreachable")

    monkeypatch.setattr(data, "ROOT", tmp_path)
    monkeypatch.setattr(data, "urlopen", offline)
    with pytest.raises(RuntimeError, match="Could not download stats.csv .*internet access"):
        data.download()


def test_truncated_download_is_rejected_and_not_saved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(data, "ROOT", tmp_path)
    monkeypatch.setattr(data, "urlopen", lambda url, timeout: FakeResponse(b"404: Not Found"))
    with pytest.raises(ValueError, match="Unexpected download for stats.csv"):
        data.download()
    assert not (tmp_path / "data/raw/stats.csv").exists()
