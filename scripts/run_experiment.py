"""So sánh mô hình bằng cách giữ riêng từng pin để kiểm thử. Tham số cố định."""
import os
import tempfile
os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "battery-soh-matplotlib"))
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import LeaveOneGroupOut

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.features import FEATURES, extract_window, validate_target


def models():
    return {
        "Mean baseline": (DummyRegressor(strategy="mean"), ["cycle"]),
        "Cycle Ridge": (make_pipeline(StandardScaler(), Ridge(alpha=1.0)), ["cycle"]),
        "Signal Ridge": (make_pipeline(StandardScaler(), Ridge(alpha=10.0)), FEATURES),
        "Random Forest": (RandomForestRegressor(n_estimators=200, min_samples_leaf=5,
                                                random_state=42, n_jobs=2), FEATURES),
        "HistGradientBoosting": (HistGradientBoostingRegressor(max_iter=150,
                                      max_leaf_nodes=15, l2_regularization=1.0,
                                      early_stopping=False, random_state=42), FEATURES),
    }


def main():
    report = ROOT / "reports"
    report.mkdir(exist_ok=True)
    manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
    # Mỗi dòng là một chu kỳ xả, không phải một thời điểm đo.
    data = pd.read_csv(ROOT / "data/clean/cycle_features.csv")
    exclusions = pd.read_csv(report / "excluded_cycles.csv")
    expected = set(manifest["primary_batteries"])
    if set(data.battery.unique()) != expected or len(data) < 30:
        raise ValueError("Chưa đủ các pin và chu kỳ trong manifest; chạy prepare_data.py")
    data.to_csv(report / "features.csv", index=False)
    # Bốn vòng: mỗi vòng học từ ba pin và dự đoán pin còn lại.
    scores, predictions = [], []
    for train, test in LeaveOneGroupOut().split(data, groups=data.battery):
        assert set(data.iloc[train].battery).isdisjoint(data.iloc[test].battery)
        for name, (model, columns) in models().items():
            model.fit(data.iloc[train][columns], data.iloc[train].soh_pct)
            y = data.iloc[test].soh_pct
            pred = model.predict(data.iloc[test][columns])
            battery = data.iloc[test].battery.iloc[0]
            scores.append(dict(model=name, held_out_battery=battery, n_train=len(train),
                n_test=len(test), mae=mean_absolute_error(y, pred),
                rmse=root_mean_squared_error(y, pred), r2=r2_score(y, pred)))
            for row, value in zip(data.iloc[test].itertuples(), pred):
                predictions.append(dict(model=name, battery=row.battery,
                    cycle=row.cycle, actual_soh=row.soh_pct, predicted_soh=float(value)))
    scores = pd.DataFrame(scores)
    predictions = pd.DataFrame(predictions)
    summary = scores.groupby("model", sort=False)[["mae", "rmse", "r2"]].mean().reset_index()
    scores.to_csv(report / "metrics_by_battery.csv", index=False)
    summary.to_csv(report / "metrics_summary.csv", index=False)
    predictions.to_csv(report / "predictions.csv", index=False)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharey=True)
    axes = axes.ravel()
    for ax, battery in zip(axes, sorted(data.battery.unique())):
        part = predictions[(predictions.battery == battery) & (predictions.model == "Random Forest")]
        ax.plot(part.cycle, part.actual_soh, label="Measured SOH")
        ax.plot(part.cycle, part.predicted_soh, label="Held-out RF prediction")
        ax.set(title=battery, xlabel="Discharge cycle", ylabel="SOH (%)")
        ax.legend(fontsize=8)
        ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(report / "held_out_predictions.png", dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(summary.model, summary.mae)
    ax.set(ylabel="Macro MAE (SOH percentage points)", title="Leave-one-battery-out; fixed parameters")
    ax.tick_params(axis="x", labelrotation=15)
    fig.tight_layout()
    fig.savefig(report / "model_comparison.png", dpi=180)
    plt.close(fig)
    # Chọn RF cố định cho demo, không chọn theo điểm kiểm thử.
    # Mô hình demo học lại cả 4 pin nên không dùng đánh giá chất lượng.
    model, columns = models()["Random Forest"]
    model.fit(data[columns], data.soh_pct)
    artifact_dir = ROOT / "artifacts"
    artifact_dir.mkdir(exist_ok=True)
    joblib.dump(dict(model=model, features=columns, training_min=data[columns].min().to_dict(),
                     training_max=data[columns].max().to_dict(), window_seconds=120,
                     batteries=sorted(data.battery.unique()), nominal_capacity_ah=2.0),
                artifact_dir / "random_forest.joblib")
    metadata = dict(run_utc=datetime.now(timezone.utc).isoformat(), seed=42,
        python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
        sklearn=sklearn.__version__, dataset_commit=manifest["commit"],
        n_cycles=len(data), n_excluded=len(exclusions), features=FEATURES,
        validation="LeaveOneGroupOut by battery; no tuning; macro mean across 4 batteries",
        demo_model="Random Forest refit on all primary data; demo predictions are not test results",
        parameters={name:model.get_params(deep=False) for name,(model,_) in models().items()})
    (report / "run_metadata.json").write_text(json.dumps(metadata, indent=2, default=str) + "\n")
    print(summary.to_string(index=False))
    print(f"Validated {len(data)} cycles; exclusions={len(exclusions)}; 20 fitted evaluation models")


if __name__ == "__main__":
    main()
