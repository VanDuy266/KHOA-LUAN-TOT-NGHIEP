"""Bounded, read-only data access shared by the standalone HTTP endpoints."""
from pathlib import Path
from functools import lru_cache
import json
import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PHASES = {"primary": "Sử dụng ban đầu", "second_life": "Tái sử dụng"}
MODELS = {"Random Forest": "random_forest.joblib", "Ridge-RF residual": "ridge_residual_forest.joblib", "CatBoost": "boosting/catboost.joblib", "XGBoost": "boosting/xgboost.joblib"}

@lru_cache(maxsize=12)
def table(relative):
    path = ROOT / relative
    if not path.exists() and path.suffix == ".csv":
        path = path.with_suffix(".csv.gz")
    return pd.read_csv(path)

@lru_cache(maxsize=12)
def metadata(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))

@lru_cache(maxsize=2)
def artifact(relative):
    result = joblib.load(ROOT / "artifacts" / relative)
    if hasattr(result.get("model"), "n_jobs"):
        result["model"].n_jobs = 2
    return result


def cycle_measurements(battery, cycle, phase):
    if phase not in PHASES or battery not in set(table("reports/features.csv").battery):
        raise ValueError("Pin hoặc giai đoạn không hợp lệ.")
    return pd.read_parquet(ROOT / "data/clean/cells" / f"{phase}_{battery}.parquet", filters=[("cycle", "=", int(cycle))])


@lru_cache(maxsize=1)
def evaluation_metrics():
    """Small summary only: homepage must not load all held-out predictions."""
    frames=[table("reports/metrics_summary.csv")]
    if (ROOT / "reports/hybrid_comparison.csv").exists():
        extra=table("reports/hybrid_comparison.csv")
        frames.append(extra[extra.model=="Ridge-RF residual"])
    if (ROOT / "reports/boosting/metadata.json").exists():
        frames.append(table("reports/boosting/metrics_summary.csv"))
    return pd.concat(frames,ignore_index=True).drop_duplicates("model",keep="last")


@lru_cache(maxsize=1)
def evaluation_results():
    """Unify saved held-out results without changing source reports or refitting."""
    import numpy as np
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    metrics = table("reports/metrics_summary.csv").copy()
    batteries = table("reports/metrics_by_battery.csv").copy()
    predictions = table("reports/predictions.csv").copy()
    phases = table("reports/metrics_by_phase.csv").copy()
    timings = table("reports/timings.csv").copy()
    hybrid = "Ridge-RF residual"
    if (ROOT / "reports/hybrid_comparison.csv").exists():
        extra = table("reports/hybrid_comparison.csv")
        metrics = pd.concat([metrics[metrics.model != hybrid], extra[extra.model == hybrid]], ignore_index=True)
        batteries = pd.concat([batteries[batteries.model != hybrid], table("reports/hybrid_by_battery.csv")], ignore_index=True)
        hybrid_predictions = table("reports/hybrid_predictions.csv")
        predictions = pd.concat([predictions[predictions.model != hybrid], hybrid_predictions], ignore_index=True)
        rows = []
        for phase, part in hybrid_predictions.groupby("phase"):
            rows.append(dict(model=hybrid, phase=phase, n_test=len(part),
                mae=mean_absolute_error(part.actual_soh, part.predicted_soh),
                rmse=np.sqrt(mean_squared_error(part.actual_soh, part.predicted_soh)),
                r2=r2_score(part.actual_soh, part.predicted_soh)))
        phases = pd.concat([phases[phases.model != hybrid], pd.DataFrame(rows)], ignore_index=True)
        rows = []
        for record in metadata("reports/hybrid_metadata.json").get("timings", []):
            row = dict(record, model=hybrid)
            row["n_test"] = int((hybrid_predictions.fold == row["fold"]).sum())
            row["n_train"] = len(hybrid_predictions) - row["n_test"]
            rows.append(row)
        timings = pd.concat([timings[timings.model != hybrid], pd.DataFrame(rows)], ignore_index=True)
    if (ROOT / "reports/boosting/metadata.json").exists():
        metrics = pd.concat([metrics, table("reports/boosting/metrics_summary.csv")], ignore_index=True)
        batteries = pd.concat([batteries, table("reports/boosting/metrics_by_battery.csv")], ignore_index=True)
        bp = table("reports/boosting/predictions.csv")
        predictions = pd.concat([predictions, bp], ignore_index=True)
        rows = []
        for (name, phase), part in bp.groupby(["model", "phase"]):
            rows.append(dict(model=name, phase=phase, n_test=len(part),
                mae=mean_absolute_error(part.actual_soh, part.predicted_soh),
                rmse=np.sqrt(mean_squared_error(part.actual_soh, part.predicted_soh)),
                r2=r2_score(part.actual_soh, part.predicted_soh)))
        phases = pd.concat([phases, pd.DataFrame(rows)], ignore_index=True)
        timings = pd.concat([timings, table("reports/boosting/timings.csv")], ignore_index=True)
    order = [hybrid, "Random Forest", "CatBoost", "XGBoost", "LightGBM", "GRU", "Ridge", "Mean baseline"]
    def ordered(frame, columns):
        return frame.assign(_order=frame.model.map({name: i for i, name in enumerate(order)})).sort_values(["_order", *columns]).drop(columns="_order").reset_index(drop=True)
    return (ordered(metrics, []), ordered(batteries, ["held_out_battery"]),
            predictions, ordered(phases, ["phase"]), ordered(timings, ["fold"]))
