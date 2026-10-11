"""Run the preregistered, fixed-parameter leave-one-battery-out comparison."""
import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/battery-soh-matplotlib")
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
    manifest = json.loads((ROOT / "data/manifest.json").read_text())
    records, audit, exclusions = [], [], []
    for item in manifest["files"]:
        p = ROOT / "data/raw" / item["name"]
        if hashlib.sha256(p.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Checksum mismatch: {p.name}")
        df = pd.read_csv(p)
        battery = item["name"].split("_")[0]
        primary = battery in manifest["primary_batteries"]
        audit.append(dict(battery=battery, rows=len(df), cycles=df.cycle.nunique(),
                          missing_values=int(df.isna().sum().sum()),
                          min_soh_pct=float(df.SOH.min()*100),
                          max_soh_pct=float(df.SOH.max()*100),
                          zero_capacity_cycles=int(df.loc[df.capacity <= 0, "cycle"].nunique()),
                          primary=primary))
        if not primary:
            continue
        for cycle, group in df.groupby("cycle", sort=True):
            try:
                target = validate_target(group)
                record = extract_window(group, cycle)
            except ValueError as error:
                exclusions.append(dict(battery=battery, cycle=int(cycle), reason=str(error)))
                continue
            records.append(dict(battery=battery, soh_pct=target, **record))
    pd.DataFrame(audit).to_csv(report / "data_audit.csv", index=False)
    pd.DataFrame(exclusions, columns=["battery", "cycle", "reason"]).to_csv(report / "excluded_cycles.csv", index=False)
    data = pd.DataFrame(records)
    if len(data) < 30 or data.battery.nunique() != 3:
        raise ValueError("Thực nghiệm yêu cầu đủ ba pin và ít nhất 30 chu kỳ hợp lệ")
    data.to_csv(report / "features.csv", index=False)
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
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
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
    # Fixed demo choice decided before viewing scores; not selected on test performance.
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
        validation="LeaveOneGroupOut by battery; no tuning; macro mean across 3 batteries",
        demo_model="Random Forest refit on all primary data; demo predictions are not test results",
        parameters={name:model.get_params(deep=False) for name,(model,_) in models().items()})
    (report / "run_metadata.json").write_text(json.dumps(metadata, indent=2, default=str) + "\n")
    print(summary.to_string(index=False))
    print(f"Validated {len(data)} cycles; exclusions={len(exclusions)}; 15 fitted evaluation models")


if __name__ == "__main__":
    main()
