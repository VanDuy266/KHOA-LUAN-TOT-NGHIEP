"""Tạo mô hình demo cố định, loại SDU_01 ở cả hai giai đoạn."""

import hashlib
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.base import clone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.features import FEATURES


def main():
    source = ROOT / "reports/features.csv"
    data = pd.read_csv(source)
    held_out = "SDU_01"  # Chọn cố định trước khi xem sai số demo.
    train = data[data.battery != held_out]
    test = data[data.battery == held_out]
    if train.empty or test.empty:
        raise ValueError("Thiếu dữ liệu học hoặc pin demo.")
    original = joblib.load(ROOT / "artifacts/random_forest.joblib")
    estimator = clone(original["model"])
    estimator.fit(train[FEATURES], train.soh_pct)
    artifact = dict(
        model=estimator, features=FEATURES, dataset="SDU",
        nominal_capacity_ah=2.4, window_seconds=120,
        batteries=sorted(train.battery.unique()), held_out_battery=held_out,
        training_min=train[FEATURES].min().to_dict(),
        training_max=train[FEATURES].max().to_dict(),
        data_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        n_train=len(train), n_test=len(test),
    )
    assert held_out not in artifact["batteries"]
    joblib.dump(artifact, ROOT / "artifacts/random_forest_demo.joblib", compress=3)
    print(f"Saved demo: {len(train)} training cycles; {len(test)} held-out cycles.")


if __name__ == "__main__":
    main()
