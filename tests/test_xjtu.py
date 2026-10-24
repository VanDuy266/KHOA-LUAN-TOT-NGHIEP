import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.xjtu import cycle_window, read_cell, normalized_features


def make_cycle(capacity=2.0):
    n = 141
    return {"system_time": pd.date_range("2024-01-01", periods=n, freq="s").strftime("%Y-%m-%d,%H:%M:%S").to_numpy(),
            "voltage_V": np.linspace(4.1, 3.8, n), "current_A": np.full(n, -2.0),
            "temperature_C": np.linspace(25, 26, n), "capacity_Ah": np.linspace(0, capacity, n),
            "description": "2C charge and 1C discharge"}


def test_xjtu_uses_absolute_time_not_resetting_step_time():
    cycle = make_cycle()
    cycle["relative_time_min"] = np.tile(np.arange(47), 3) / 60
    window, capacity, _ = cycle_window(cycle)
    assert window.time.tolist() == list(range(121))
    assert capacity == 2.0


def test_duplicate_second_aggregation_preserves_source():
    cycle = make_cycle()
    cycle["system_time"][11] = cycle["system_time"][10]
    before = cycle["voltage_V"].copy()
    window, _, duplicates = cycle_window(cycle)
    assert duplicates == 1
    assert not window.time.duplicated().any()
    assert window.loc[window.time == 10, "terminal_voltage"].item() == pytest.approx(before[10:12].mean())
    np.testing.assert_array_equal(cycle["voltage_V"], before)


def test_capacity_target_does_not_enter_features(monkeypatch):
    import battery_soh.xjtu as module
    output = []
    for capacity in [2.0, 1.6]:
        monkeypatch.setattr(module, "loadmat", lambda *a, cap=capacity, **kw:
                            {"data": [make_cycle(cap)], "summary": {"description":"2C charge experiment", "discharge_capacity_Ah": [cap]}})
        frame, _, _, rejected, _ = read_cell(None, "TEST", 1)
        assert not rejected
        output.append(frame)
    pd.testing.assert_frame_equal(normalized_features(output[0], 2), normalized_features(output[1], 2))
    assert output[0].soh_pct.item() == 100
    assert output[1].soh_pct.item() == 80


def test_current_normalization_uses_nominal_not_measured_capacity():
    import battery_soh.xjtu as module
    columns = module.TRANSFER_FEATURES
    frame = pd.DataFrame({c: [1.] for c in columns})
    frame["current_mean"], frame["current_std"], frame["capacity_ah"] = -2., 0.2, 0.01
    result = normalized_features(frame, 2)
    assert result.current_mean.item() == -1
    assert result.current_std.item() == 0.1
    assert "capacity_ah" not in result and "phase_code" not in result


def test_reference_capacity_mismatch_is_excluded(monkeypatch):
    import battery_soh.xjtu as module
    monkeypatch.setattr(module, "loadmat", lambda *a, **kw:
                        {"data": [make_cycle(2)], "summary": {"description":"2C charge experiment", "discharge_capacity_Ah": [1.2]}})
    frame, _, _, rejected, audit = read_cell(None, "TEST", 1)
    assert frame.empty and audit["excluded_cycles"] == 1
    assert "0,005" in rejected[0]["reason"]


def test_xjtu_group_splits_and_predictions_are_complete():
    frame = pd.read_csv(ROOT / "reports/xjtu/features.csv")
    frame = frame.loc[frame.cycle > 1]
    split = pd.read_csv(ROOT / "reports/xjtu/split_assignments.csv")
    predictions = pd.read_csv(ROOT / "reports/xjtu/predictions.csv")
    assert split.battery.nunique() == 23 and not split.battery.duplicated().any()
    assert set(frame.battery) == set(split.battery)
    held = predictions[predictions.design == "XJTU held-out"]
    assert set(held.model) == {"Mean baseline", "Ridge", "Random Forest", "LightGBM", "Ridge-RF residual", "RF multi-source", "GRU"}
    for _, part in held.groupby("model"):
        assert len(part) == len(frame)
        assert not part.duplicated(["battery", "cycle"]).any()
        check = part.merge(split, on="battery", validate="many_to_one")
        assert (check.fold == check.test_fold).all()
    assert np.isfinite(predictions[["actual_soh", "predicted_soh"]]).all().all()


def test_xjtu_app_and_forecast_render():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=30).run()
    app.radio(key="navigation").set_value("Thực nghiệm XJTU").run()
    assert not app.exception and not app.error
    app.radio(key="xjtu_mode").set_value("Dự đoán XJTU").run()
    app.button(key="xjtu_predict").click().run()
    assert not app.exception and not app.error
    assert "xjtu_prediction" in app.session_state
    app.selectbox(key="xjtu_predict_model").set_value("RF multi-source").run()
    assert len(app.dataframe) == 0  # Không giữ kết quả của mô hình trước khi đổi đầu vào.
    app.button(key="xjtu_predict").click().run()
    assert not app.exception and not app.error


def test_uploaded_batch_must_match_original_protocol(monkeypatch):
    import battery_soh.xjtu as module
    monkeypatch.setattr(module, "loadmat", lambda *a, **kw:
                        {"data": [make_cycle(2)], "summary": {"description":"3C charge experiment", "discharge_capacity_Ah": [2]}})
    with pytest.raises(ValueError, match="không khớp Batch-1"):
        read_cell(None, "TEST", 1)
