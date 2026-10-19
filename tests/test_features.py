import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.features import FEATURES, extract_window, validate_target


@pytest.fixture
def cycle():
    return pd.DataFrame(
        {
            "time": [0, 20, 40, 60, 80, 100, 120, 140, 3000],
            "terminal_voltage": [4.2, 4.1, 4.0, 3.99, 3.98, 3.97, 3.96, 3.95, 2.7],
            "terminal_current": [-0.001] + [-2.0] * 8,
            "temperature": [24.0, 24.0, 24.1, 24.2, 24.3, 24.4, 24.5, 24.6, 30.0],
            "phase_code": [0] * 9,
            "capacity": [2.16] * 9,
            "SOH": [0.9] * 9,
        }
    )


def test_future_signals_and_target_do_not_change_features(cycle):
    before = extract_window(cycle, 1)
    cycle.loc[
        cycle.time > 120, ["terminal_voltage", "terminal_current", "temperature"]
    ] = np.nan
    cycle["capacity"] = 0
    cycle["SOH"] = 0
    assert extract_window(cycle, 1) == before
    assert not {"capacity", "SOH", "soh_pct", "discharge_duration"}.intersection(
        FEATURES
    )


def test_exact_window_boundary(cycle):
    before = extract_window(cycle, 1)
    cycle.loc[cycle.time == 120, "terminal_voltage"] = 3.5
    assert extract_window(cycle, 1)["voltage_min"] < before["voltage_min"]


@pytest.mark.parametrize(
    "column", ["time", "terminal_voltage", "terminal_current", "temperature"]
)
def test_missing_required_columns(cycle, column):
    with pytest.raises(ValueError, match="Thiếu cột"):
        extract_window(cycle.drop(columns=column), 1)


def test_incomplete_window(cycle):
    with pytest.raises(ValueError, match="ít nhất 5 mẫu"):
        extract_window(cycle[cycle.time < 90], 1)


def test_duplicate_timestamp(cycle):
    cycle.loc[1, "time"] = 0
    with pytest.raises(ValueError, match="trùng"):
        extract_window(cycle, 1)


def test_rejects_non_discharge(cycle):
    cycle["terminal_current"] = 2
    with pytest.raises(ValueError, match="mẫu xả"):
        extract_window(cycle, 1)


def test_rejects_missing_observed_signal(cycle):
    cycle.loc[2, "terminal_voltage"] = np.nan
    with pytest.raises(ValueError, match="thiếu hoặc vô hạn"):
        extract_window(cycle, 1)


def test_label_definition(cycle):
    assert validate_target(cycle) == pytest.approx(90)
    cycle["SOH"] = 0.8
    with pytest.raises(ValueError, match="không khớp"):
        validate_target(cycle)


def test_label_consistency(cycle):
    cycle.loc[2, "capacity"] = 1.2
    with pytest.raises(ValueError, match="không nhất quán"):
        validate_target(cycle)


def test_rejects_empty_labels(cycle):
    with pytest.raises(ValueError, match="Thiếu dữ liệu"):
        validate_target(cycle.iloc[:0])


def test_saved_artifact_matches_features():
    import joblib

    artifact = joblib.load(ROOT / "artifacts/random_forest.joblib")
    data = pd.read_csv(ROOT / "reports/features.csv")
    predictions = artifact["model"].predict(data[FEATURES].head())
    assert artifact["features"] == FEATURES
    assert np.isfinite(predictions).all()


def test_evaluation_covers_each_battery_once_per_model():
    metrics = pd.read_csv(ROOT / "reports/metrics_by_battery.csv")
    data = pd.read_csv(ROOT / "reports/features.csv")
    pred = pd.read_csv(ROOT / "reports/predictions.csv")
    assert len(metrics) == 86 * 5
    assert not pred.duplicated(["model", "battery", "phase", "cycle"]).any()
    assert pred.groupby("model").size().eq(len(data)).all()
    for row in metrics.itertuples():
        assert row.n_test == (data.battery == row.held_out_battery).sum()
        split = pd.read_csv(ROOT / "reports/split_assignments.csv")
        held_pins = set(split.loc[split.test_fold == row.fold, "battery"])
        assert row.held_out_battery in held_pins
        assert row.n_train == (~data.battery.isin(held_pins)).sum()


def test_reported_metrics_match_saved_held_out_predictions():
    from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

    metrics = pd.read_csv(ROOT / "reports/metrics_by_battery.csv")
    predictions = pd.read_csv(ROOT / "reports/predictions.csv")
    for row in metrics.itertuples():
        part = predictions[
            (predictions.model == row.model)
            & (predictions.battery == row.held_out_battery)
        ]
        assert row.mae == pytest.approx(
            mean_absolute_error(part.actual_soh, part.predicted_soh)
        )
        assert row.rmse == pytest.approx(
            root_mean_squared_error(part.actual_soh, part.predicted_soh)
        )
        assert row.r2 == pytest.approx(r2_score(part.actual_soh, part.predicted_soh))
