"""Refit hai mô hình ứng dụng từ bảng đặc trưng; không thay điểm kiểm thử."""
from pathlib import Path
import hashlib
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.xjtu import normalized_features, TRANSFER_FEATURES


def forest():
    return RandomForestRegressor(n_estimators=100, min_samples_leaf=5, max_depth=16,
                                 max_samples=.7, random_state=42, n_jobs=2)


def main():
    data = pd.read_csv(ROOT / "reports/xjtu/features.csv")
    data = data.loc[data.cycle > 1].reset_index(drop=True)
    sdu = pd.read_csv(ROOT / "reports/features.csv")
    x = normalized_features(data, 2.0)
    source = normalized_features(sdu, 2.4)
    y = data.soh_pct.to_numpy()
    pooled_x = pd.concat([source, x], ignore_index=True)
    pooled_y = np.concatenate([sdu.soh_pct.to_numpy(), y])
    weights = np.concatenate([np.full(len(source), .5/len(source)), np.full(len(x), .5/len(x))])
    output = ROOT / "artifacts/xjtu"
    output.mkdir(parents=True, exist_ok=True)
    for name, fitted, training, dataset in [
        ("random_forest", forest().fit(x, y), x, "XJTU"),
        ("multi_source_forest", forest().fit(pooled_x, pooled_y, sample_weight=weights), pooled_x, "SDU+XJTU")]:
        joblib.dump({"model": fitted, "dataset": dataset, "features": TRANSFER_FEATURES,
                     "nominal_capacity_ah":2.0, "batteries":sorted(data.battery.unique()),
                     "training_min":training.min().to_dict(), "training_max":training.max().to_dict(),
                     "features_sha256": hashlib.sha256((ROOT / "reports/xjtu/features.csv").read_bytes()).hexdigest(),
                     "scope":"Refit on all source training cells; not held-out evaluation"}, output / (name + ".joblib"))
    print("Đã refit RF riêng XJTU và RF đa nguồn cho ứng dụng.", flush=True)


if __name__ == "__main__":
    main()
