"""Phát hiện thiếu pin, sai nhãn hoặc lẫn dữ liệu giữa các tập kiểm thử SDU."""

import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_full_sdu_dataset_verified():
    check = json.loads((ROOT / "reports/dataset_check.json").read_text())
    assert check["status"] == "passed" and check["dataset"] == "SDU"
    assert check["measurement_rows"] == 10_000_000
    assert check["independent_batteries"] == 86
    assert check["missing_values"] == check["duplicate_measurement_keys"] == 0
    assert check["nominal_capacity_ah"] == 2.4


def test_feature_labels_and_sample_count():
    data = pd.read_csv(ROOT / "data/clean/cycle_features.csv")
    labels = pd.read_csv(ROOT / "data/clean/cycle_labels.csv")
    summary = json.loads((ROOT / "reports/dataset_summary.json").read_text())
    assert len(data) == summary["feature_rows"] and data.battery.nunique() == 86
    assert not data.duplicated(["battery", "phase", "cycle"]).any()
    assert np.isfinite(data.select_dtypes("number").to_numpy()).all()
    merged = data.merge(labels, on=["battery", "phase", "cycle"], validate="one_to_one")
    assert len(merged) == len(data)
    assert np.allclose(merged.soh_pct_x, merged.capacity_ah_y / 2.4 * 100)
    assert "temperature_mean" in data.columns and set(data.phase_code) == {0, 1}


def test_five_fold_split_has_no_battery_leakage():
    split = pd.read_csv(ROOT / "reports/split_assignments.csv")
    data = pd.read_csv(ROOT / "reports/features.csv")
    assert len(split) == 86 and split.battery.nunique() == 86
    assert set(split.test_fold) == {1, 2, 3, 4, 5}
    pred = pd.read_csv(ROOT / "reports/predictions.csv")
    assert pred.groupby(["model", "battery", "phase", "cycle"]).size().eq(1).all()
    joined = pred.merge(split, on="battery", validate="many_to_one")
    assert joined.fold.eq(joined.test_fold).all()
    assert pred.groupby("model").size().eq(len(data)).all()


def test_temporal_split_is_strictly_forward():
    metrics = pd.read_csv(ROOT / "reports/temporal_metrics.csv")
    assert len(metrics) == 86 * 2 * 2
    assert (metrics.last_train_cycle < metrics.first_test_cycle).all()
