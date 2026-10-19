"""So sánh mô hình bằng cách giữ riêng từng pin để kiểm thử. Tham số cố định."""

import os
import tempfile

os.environ.setdefault(
    "MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "battery-soh-matplotlib")
)
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
import time
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
from sklearn.ensemble import RandomForestRegressor
from lightgbm import LGBMRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.features import FEATURES, extract_window, validate_target


def models():
    return {
        "Mean baseline": (DummyRegressor(strategy="mean"), ["cycle"]),
        "Ridge": (make_pipeline(StandardScaler(), Ridge(alpha=10.0)), FEATURES),
        "Random Forest": (
            RandomForestRegressor(
                n_estimators=100,
                min_samples_leaf=5,
                max_depth=16,
                max_samples=0.7,
                random_state=42,
                n_jobs=2,
            ),
            FEATURES,
        ),
        "LightGBM": (
            LGBMRegressor(
                n_estimators=150,
                num_leaves=15,
                learning_rate=0.05,
                reg_lambda=1.0,
                random_state=42,
                n_jobs=2,
                verbosity=-1,
            ),
            FEATURES,
        ),
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
        raise ValueError(
            "Chưa đủ các pin và chu kỳ trong manifest; chạy prepare_data.py"
        )
    data.to_csv(report / "features.csv", index=False)
    data_sha256 = hashlib.sha256(
        (ROOT / "data/clean/cycle_features.csv").read_bytes()
    ).hexdigest()
    # Năm vòng, mỗi pin chỉ thuộc một tập kiểm thử; không trùng pin giữa học và kiểm thử.
    scores, predictions, timings = [], [], []
    split_rows = []
    for fold, (train, test) in enumerate(
        GroupKFold(n_splits=5, shuffle=True, random_state=42).split(
            data, groups=data.battery
        ),
        1,
    ):
        print(f"Kiểm thử nhóm pin: vòng {fold}/5", flush=True)
        for pin in sorted(data.iloc[test].battery.unique()):
            split_rows.append(dict(battery=pin, test_fold=fold))
        assert set(data.iloc[train].battery).isdisjoint(data.iloc[test].battery)
        for name, (model, columns) in models().items():
            start = time.perf_counter()
            model.fit(data.iloc[train][columns], data.iloc[train].soh_pct)
            fit_seconds = time.perf_counter() - start
            y = data.iloc[test].soh_pct
            start = time.perf_counter()
            pred = model.predict(data.iloc[test][columns])
            timings.append(
                dict(
                    model=name,
                    fold=fold,
                    fit_seconds=fit_seconds,
                    predict_seconds=time.perf_counter() - start,
                    n_train=len(train),
                    n_test=len(test),
                )
            )
            tested = data.iloc[test].copy()
            tested["prediction"] = pred
            for battery, part in tested.groupby("battery"):
                scores.append(
                    dict(
                        model=name,
                        fold=fold,
                        held_out_battery=battery,
                        n_train=len(train),
                        n_test=len(part),
                        mae=mean_absolute_error(part.soh_pct, part.prediction),
                        rmse=root_mean_squared_error(part.soh_pct, part.prediction),
                        r2=r2_score(part.soh_pct, part.prediction),
                    )
                )
            for row, value in zip(data.iloc[test].itertuples(), pred):
                predictions.append(
                    dict(
                        model=name,
                        fold=fold,
                        battery=row.battery,
                        phase=row.phase,
                        cycle=row.cycle,
                        actual_soh=row.soh_pct,
                        predicted_soh=float(value),
                    )
                )
            print(f"  {name}: xong", flush=True)
    pd.DataFrame(split_rows).to_csv(report / "split_assignments.csv", index=False)
    pd.DataFrame(timings).to_csv(report / "timings.csv", index=False)
    scores = pd.DataFrame(scores)
    predictions = pd.DataFrame(predictions)
    summary = (
        scores.groupby("model", sort=False)[["mae", "rmse", "r2"]].mean().reset_index()
    )
    scores.to_csv(report / "metrics_by_battery.csv", index=False)
    summary.to_csv(report / "metrics_summary.csv", index=False)
    predictions.to_csv(report / "predictions.csv", index=False)
    phase_scores = []
    for (name, phase), part in predictions.groupby(["model", "phase"]):
        phase_scores.append(
            dict(
                model=name,
                phase=phase,
                mae=mean_absolute_error(part.actual_soh, part.predicted_soh),
                rmse=root_mean_squared_error(part.actual_soh, part.predicted_soh),
                r2=r2_score(part.actual_soh, part.predicted_soh),
                n_test=len(part),
            )
        )
    pd.DataFrame(phase_scores).to_csv(report / "metrics_by_phase.csv", index=False)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharey=True)
    axes = axes.ravel()
    for ax, battery in zip(axes, sorted(data.battery.unique())[:4]):
        part = predictions[
            (predictions.battery == battery) & (predictions.model == "Random Forest")
        ]
        for phase, group in part.groupby("phase"):
            group = group.sort_values("cycle")
            ax.plot(group.cycle, group.actual_soh, label=phase + " actual")
            ax.plot(
                group.cycle, group.predicted_soh, linestyle="--", label=phase + " RF"
            )
        ax.set(title=battery, xlabel="Discharge cycle", ylabel="SOH (%)")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(report / "held_out_predictions.png", dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(summary.model, summary.mae)
    ax.set(
        ylabel="Macro MAE (SOH percentage points)",
        title="SDU: 5-fold grouped by battery; fixed parameters",
    )
    ax.tick_params(axis="x", labelrotation=15)
    fig.tight_layout()
    fig.savefig(report / "model_comparison.png", dpi=180)
    plt.close(fig)
    # Chọn RF cố định cho demo, không chọn theo điểm kiểm thử.
    # Mô hình ứng dụng học lại toàn bộ pin; điểm kiểm thử lấy từ các vòng riêng.
    model, columns = models()["Random Forest"]
    model.fit(data[columns], data.soh_pct)
    pd.DataFrame({"feature": columns, "importance": model.feature_importances_}).to_csv(
        report / "feature_importance.csv", index=False
    )
    artifact_dir = ROOT / "artifacts"
    artifact_dir.mkdir(exist_ok=True)
    joblib.dump(
        dict(
            model=model,
            features=columns,
            training_min=data[columns].min().to_dict(),
            training_max=data[columns].max().to_dict(),
            window_seconds=120,
            batteries=sorted(data.battery.unique()),
            nominal_capacity_ah=2.4,
            dataset="SDU",
        ),
        artifact_dir / "random_forest.joblib",
    )
    metadata = dict(
        run_utc=datetime.now(timezone.utc).isoformat(),
        seed=42,
        python=platform.python_version(),
        numpy=np.__version__,
        pandas=pd.__version__,
        sklearn=sklearn.__version__,
        dataset_commit=manifest["commit"],
        data_sha256=data_sha256,
        n_cycles=len(data),
        dataset="SDU",
        n_excluded=len(exclusions),
        features=FEATURES,
        validation="5-fold GroupKFold by battery; shuffle=True, seed=42; no tuning; macro mean across 86 physical batteries",
        demo_model="Random Forest refit on all selected cycles from both phases; demo predictions are not test results",
        parameters={
            name: model.get_params(deep=False) for name, (model, _) in models().items()
        },
    )
    (report / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, default=str) + "\n"
    )
    print(summary.to_string(index=False))
    print(
        f"Validated {len(data)} cycles; exclusions={len(exclusions)}; 20 fitted evaluation models"
    )


if __name__ == "__main__":
    main()
