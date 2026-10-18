"""Các kiểm tra có thể phát hiện mất dữ liệu, sai nhãn hoặc trộn chu kỳ."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from prepare_data import clean_battery


def test_dataset_verified_over_two_million_rows():
    check = json.loads((ROOT / "reports/dataset_check.json").read_text())
    assert check["status"] == "passed"
    assert check["measurement_rows"] >= 2_000_000
    assert check["source_arrays_match"] is True
    assert check["missing_values"] == check["duplicate_measurement_keys"] == 0
    assert check["independent_batteries"] == 4


def test_cleaning_only_removes_invalid_measurement_rows():
    frame = pd.DataFrame({"battery": ["B0005"]*3, "operation_index": [1]*3,
        "time": [0., 1., 2.], "terminal_voltage": [4., np.nan, 3.9],
        "terminal_current": [-2.]*3, "temperature": [25.]*3, "ambient_temperature": [24.]*3})
    cleaned = clean_battery(frame)
    assert cleaned.time.to_list() == [0., 2.]
    assert cleaned.terminal_voltage.to_list() == [4., 3.9]


def test_cleaning_rejects_conflicting_time_keys():
    frame = pd.DataFrame({"battery": ["B0005"]*2, "operation_index": [1]*2,
        "time": [0., 0.], "terminal_voltage": [4., 3.9],
        "terminal_current": [-2.]*2, "temperature": [25.]*2, "ambient_temperature": [24.]*2})
    with pytest.raises(ValueError, match="xung đột"):
        clean_battery(frame)


def test_feature_samples_and_labels():
    features = pd.read_csv(ROOT / "data/clean/cycle_features.csv")
    assert len(features) == 636
    assert features.groupby("battery").size().to_dict() == {"B0005": 168, "B0006": 168, "B0007": 168, "B0018": 132}
    assert not features.isna().any().any()
    assert not features.duplicated(["battery", "cycle"]).any()
    # Dung lượng ban đầu có thể vượt 2 Ah, không tự cắt SOH về 100%.
    assert features.soh_pct.max() > 100


def test_temporal_split_is_strictly_forward():
    metrics = pd.read_csv(ROOT / "reports/temporal_metrics.csv")
    assert len(metrics) == 8
    assert (metrics.last_train_cycle < metrics.first_test_cycle).all()
