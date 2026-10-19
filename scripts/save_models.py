"""Học lại mô hình bảng trên toàn bộ dữ liệu để lưu bản bàn giao; không tạo điểm test."""

import joblib
import pandas as pd
from run_experiment import ROOT, models


def main():
    data = pd.read_csv(ROOT / "reports/features.csv")
    for name, (model, columns) in models().items():
        model.fit(data[columns], data.soh_pct)
        filename = {
            "Mean baseline": "mean_baseline",
            "Ridge": "ridge",
            "Random Forest": "random_forest",
            "LightGBM": "lightgbm",
        }[name]
        artifact = dict(
            model=model,
            features=columns,
            dataset="SDU",
            nominal_capacity_ah=2.4,
            window_seconds=120,
            batteries=sorted(data.battery.unique()),
            training_min=data[columns].min().to_dict(),
            training_max=data[columns].max().to_dict(),
        )
        joblib.dump(artifact, ROOT / "artifacts" / f"{filename}.joblib")
        print("Đã lưu", name, flush=True)


if __name__ == "__main__":
    main()
