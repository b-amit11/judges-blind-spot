import pytest
from blindspot.data import ROOT

pytestmark=pytest.mark.skipif(not (ROOT/'artifacts/model.joblib').exists(),reason='Train model before UI integration tests')


def test_review_reveal_and_sandbox():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
    assert not app.exception
    app.checkbox[0].check().run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert any('Estimated disagreement' in m.label for m in app.metric)
