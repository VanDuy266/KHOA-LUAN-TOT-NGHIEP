"""Thực nghiệm bổ sung: bỏ nhóm đặc trưng và kiểm thử theo thời gian.

Các cấu hình này là phân tích sau kết quả chính, không dùng chọn mô hình demo.
"""
import os
import tempfile
os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "battery-soh-matplotlib"))
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.model_selection import LeaveOneGroupOut

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.features import FEATURES


def create_forest():
    return RandomForestRegressor(n_estimators=200, min_samples_leaf=5,
                                 random_state=42, n_jobs=2)


def main():
    data = pd.read_csv(ROOT / "reports/features.csv")
    ablation = []
    groups = {
        "Full features": FEATURES,
        "Without cycle": [name for name in FEATURES if name != "cycle"],
        "Without temperature": [name for name in FEATURES if not name.startswith("temperature")],
    }
    for train, test in LeaveOneGroupOut().split(data, groups=data.battery):
        for name, columns in groups.items():
            model = create_forest()
            model.fit(data.iloc[train][columns], data.iloc[train].soh_pct)
            actual = data.iloc[test].soh_pct
            predicted = model.predict(data.iloc[test][columns])
            ablation.append({"configuration": name, "battery": data.iloc[test].battery.iloc[0],
                "mae": mean_absolute_error(actual, predicted),
                "rmse": root_mean_squared_error(actual, predicted)})
    ablation = pd.DataFrame(ablation)
    ablation.to_csv(ROOT / "reports/ablation_by_battery.csv", index=False)
    summary = ablation.groupby("configuration", sort=False)[["mae", "rmse"]].mean().reset_index()
    summary.to_csv(ROOT / "reports/ablation_summary.csv", index=False)

    # Bài toán khác: đã có nhãn 70% chu kỳ đầu của cùng pin.
    temporal = []
    for battery, part in data.groupby("battery"):
        part = part.sort_values("cycle")
        cutoff = int(len(part) * 0.7)
        train, test = part.iloc[:cutoff], part.iloc[cutoff:]
        model = create_forest()
        model.fit(train[FEATURES], train.soh_pct)
        forecasts = {
            "Random Forest": model.predict(test[FEATURES]),
            "Last known SOH": np.repeat(train.soh_pct.iloc[-1], len(test)),
        }
        for name, predicted in forecasts.items():
            temporal.append({"battery": battery, "model": name, "n_train": len(train), "n_test": len(test),
                "last_train_cycle": int(train.cycle.max()), "first_test_cycle": int(test.cycle.min()),
                "mae": mean_absolute_error(test.soh_pct, predicted),
                "rmse": root_mean_squared_error(test.soh_pct, predicted)})
    pd.DataFrame(temporal).to_csv(ROOT / "reports/temporal_metrics.csv", index=False)
    predictions = pd.read_csv(ROOT / "reports/predictions.csv")
    rf = predictions[predictions.model == "Random Forest"].copy()
    rf["error"] = rf.predicted_soh - rf.actual_soh
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for battery, part in rf.groupby("battery"):
        axes[0].scatter(part.actual_soh, part.predicted_soh, s=10, alpha=.6, label=battery)
        axes[1].scatter(part.cycle, part.error, s=10, alpha=.6, label=battery)
    lower, upper = rf.actual_soh.min(), rf.actual_soh.max()
    axes[0].plot([lower, upper], [lower, upper], "k--", linewidth=1)
    axes[0].set(xlabel="Measured SOH (%)", ylabel="Held-out prediction (%)")
    axes[1].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[1].set(xlabel="Discharge cycle", ylabel="Prediction error (percentage points)")
    for ax in axes:
        ax.legend(fontsize=8)
        ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(ROOT / "reports/error_analysis.png", dpi=180)
    plt.close(fig)
    print("Phân tích bỏ đặc trưng:")
    print(summary.to_string(index=False))
    print("Đã lưu kiểm thử theo thời gian riêng; không gộp với kết quả giữ riêng pin.")


if __name__ == "__main__":
    main()
