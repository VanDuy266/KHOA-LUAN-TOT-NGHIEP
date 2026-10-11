from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_demo_sample_prediction():
    app = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=30).run()
    assert not app.exception
    app.checkbox[0].check().run()
    app.button[0].click().run()
    assert not app.exception
    assert not app.error
    assert any(metric.label == "SOH ước lượng" for metric in app.metric)


def test_demo_requires_input():
    app = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=30).run()
    app.button[0].click().run()
    assert not app.exception
    assert any("Hãy tải CSV" in error.value for error in app.error)
