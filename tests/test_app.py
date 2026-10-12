from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from blindspot import data
from blindspot.data import ROOT

needs_model = pytest.mark.skipif(
    not (ROOT / "artifacts/model.joblib").exists(), reason="Train model before UI integration tests"
)


@needs_model
def test_review_reveal_and_sandbox():
    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
    assert not app.exception
    app.checkbox[0].check().run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert any("Estimated disagreement" in m.label for m in app.metric)


@needs_model
def test_queue_export_follows_filter_and_hides_outcomes():
    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
    labels = [b.label for b in app.get("download_button")]
    total = next(lbl for lbl in labels if lbl.startswith("Download full queue"))
    assert "1,101 rounds" in total
    fighter = app.selectbox[0].options[1]
    app.selectbox[0].select(fighter).run()
    assert not app.exception
    labels = [b.label for b in app.get("download_button")]
    filtered = next(lbl for lbl in labels if lbl.startswith("Download full queue"))
    assert filtered != total
    assert any("excludes observed judge outcomes" in c.value for c in app.caption)


def test_missing_artifacts_show_setup_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts/model.joblib").write_bytes(b"")
    monkeypatch.setattr(data, "ROOT", tmp_path)
    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
    assert not app.exception
    message = app.info[0].value
    assert "reports/test_predictions.csv" in message and "reports/metrics.json" in message
    assert "artifacts/model.joblib" not in message
