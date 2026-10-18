from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def open_page(name):
    app = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=30).run()
    app.radio(key="navigation").set_value(name).run()
    return app


@pytest.mark.parametrize("name", ["Tổng quan", "Tra cứu pin", "Đánh giá mô hình", "Dự đoán SOH", "Thông tin", "Lịch sử dự đoán"])
def test_each_page_renders(name):
    app = open_page(name)
    assert not app.exception
    assert not app.error


def test_demo_sample_prediction_and_result_persistence():
    app = open_page("Dự đoán SOH")
    app.checkbox[0].check().run()
    app.button[0].click().run()
    assert not app.exception
    assert not app.error
    assert any(metric.label == "SOH ước lượng" for metric in app.metric)
    app.run()
    assert any(metric.label == "SOH ước lượng" for metric in app.metric)


def test_demo_requires_input():
    app = open_page("Dự đoán SOH")
    app.button[0].click().run()
    assert not app.exception
    assert any("Hãy tải CSV" in error.value for error in app.error)


def test_sample_cannot_be_relabelled_as_another_cycle():
    app = open_page("Dự đoán SOH")
    app.checkbox[0].check().run()
    app.number_input[0].set_value(2).run()
    app.button[0].click().run()
    assert any("CSV mẫu thuộc chu kỳ 1" in error.value for error in app.error)
    assert not app.metric


def test_explorer_empty_selection_has_helpful_message():
    app = open_page("Tra cứu pin")
    app.multiselect[0].set_value([]).run()
    assert not app.exception
    assert any("Chưa có dữ liệu" in info.value for info in app.info)


def test_old_forecast_hidden_after_input_changes():
    app = open_page("Dự đoán SOH")
    app.checkbox[0].check().run()
    app.button[0].click().run()
    assert app.metric
    app.number_input[0].set_value(2).run()
    assert not app.metric


def test_batch_sample_and_session_history():
    app = open_page("Dự đoán SOH")
    app.radio(key="forecast_mode").set_value("Theo lô").run()
    app.checkbox[0].check().run()
    app.button[0].click().run()
    assert not app.exception and not app.error
    assert len(app.session_state["prediction_history"]) == 3
    app.radio(key="navigation").set_value("Lịch sử dự đoán").run()
    assert not app.exception
    assert any(metric.label == "Thành công" and str(metric.value) == "3" for metric in app.metric)
    app.button[0].click().run()
    assert any("Chưa có lịch sử" in info.value for info in app.info)


def test_product_has_new_name_without_coaching_copy():
    app = open_page("Tổng quan")
    text = " ".join(item.value for item in app.markdown)
    assert "Vincent D" in text and "PinLab" not in text
    assert "Trước khi nộp" not in text
