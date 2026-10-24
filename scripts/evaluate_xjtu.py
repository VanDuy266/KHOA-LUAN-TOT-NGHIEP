"""Kiểm thử theo pin XJTU, chuyển miền SDU và RF đa nguồn; không trộn điểm số SDU."""
import os
os.environ.setdefault("OMP_NUM_THREADS", "2")
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.features import FEATURES
from battery_soh.xjtu import normalized_features, TRANSFER_FEATURES
from battery_soh.hybrid import RidgeResidualForest
from run_experiment import models


def scores(predictions):
    rows = []
    for (design, model, battery), part in predictions.groupby(["design", "model", "battery"], sort=False):
        rows.append({"design": design, "model": model, "battery": battery, "n_test": len(part),
                     "mae": mean_absolute_error(part.actual_soh, part.predicted_soh),
                     "rmse": root_mean_squared_error(part.actual_soh, part.predicted_soh),
                     "r2": r2_score(part.actual_soh, part.predicted_soh) if len(part)>1 else np.nan})
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-gru", action="store_true")
    args = parser.parse_args()
    report = ROOT / "reports/xjtu"
    data = pd.read_csv(report / "features.csv")
    # Chu kỳ đầu đo ở 0,2C, các chu kỳ còn lại ở 1C; không trộn hai điều kiện vào đánh giá chính.
    data = data.loc[data.cycle > 1].reset_index(drop=True)
    sdu = pd.read_csv(ROOT / "reports/features.csv")
    X, S = normalized_features(data, 2.0), normalized_features(sdu, 2.4)
    y = data.soh_pct.to_numpy()
    estimators = {name: estimator for name, (estimator, _) in models().items()}
    estimators["Ridge-RF residual"] = RidgeResidualForest()
    result, timings, assignments = [], [], []

    def record(design, name, indexes, prediction, fold):
        part = data.iloc[indexes][["battery", "batch", "cycle", "soh_pct"]].copy()
        part = part.rename(columns={"soh_pct": "actual_soh"})
        part["predicted_soh"], part["design"], part["model"], part["fold"] = prediction, design, name, fold
        result.append(part)

    if not args.skip_gru:
        from train_gru import fit_predict
        stored = np.load(ROOT / "data/xjtu/processed/sequences.npz")
        expected_keys = data[["battery", "cycle"]].astype(str).agg("|".join, axis=1).to_numpy(dtype=str)
        source_keys = pd.read_csv(report / "features.csv")
        source_keys = source_keys[["battery", "cycle"]].astype(str).agg("|".join, axis=1).to_numpy(dtype=str)
        if not np.array_equal(stored["keys"], source_keys):
            raise ValueError("Chuỗi GRU khác thứ tự đặc trưng")
        key_index = pd.Index(stored["keys"]).get_indexer(expected_keys)
        if (key_index < 0).any():
            raise ValueError("Thiếu chuỗi chu kỳ kiểm thử")
        signals = stored["signals"][key_index].copy()
        signals[:, :, 1] /= 2.0
        context = data[["phase_code", "cycle"]].to_numpy(dtype="float32")

    for fold, (train, test) in enumerate(GroupKFold(n_splits=5, shuffle=True, random_state=42).split(X, groups=data.battery), 1):
        assert set(data.iloc[train].battery).isdisjoint(data.iloc[test].battery)
        assignments.extend({"battery": b, "test_fold": fold} for b in sorted(data.iloc[test].battery.unique()))
        print(f"XJTU vòng {fold}/5", flush=True)
        for name, template in estimators.items():
            start = time.perf_counter()
            estimator = clone(template).fit(X.iloc[train], y[train])
            record("XJTU held-out", name, test, estimator.predict(X.iloc[test]), fold)
            timings.append({"design": "XJTU held-out", "model": name, "fold": fold, "fit_predict_seconds": time.perf_counter()-start})
        # Cấu hình cố định trước khi chạy; cân bằng tổng trọng số giữa hai nguồn.
        pooled_x = pd.concat([S, X.iloc[train]], ignore_index=True)
        pooled_y = np.concatenate([sdu.soh_pct.to_numpy(), y[train]])
        weights = np.concatenate([np.full(len(S), 0.5/len(S)), np.full(len(train), 0.5/len(train))])
        start = time.perf_counter()
        pooled = clone(estimators["Random Forest"]).fit(pooled_x, pooled_y, sample_weight=weights)
        record("XJTU held-out", "RF multi-source", test, pooled.predict(X.iloc[test]), fold)
        timings.append({"design": "XJTU held-out", "model": "RF multi-source", "fold": fold, "fit_predict_seconds": time.perf_counter()-start})
        if not args.skip_gru:
            start = time.perf_counter()
            prediction = fit_predict(signals, context, y.astype("float32"), train, test)
            record("XJTU held-out", "GRU", test, prediction, fold)
            timings.append({"design": "XJTU held-out", "model": "GRU", "fold": fold, "fit_predict_seconds": time.perf_counter()-start})
        # Lưu dần để một lỗi ở bước sau không mất nhật ký các vòng đã hoàn thành.
        pd.concat(result, ignore_index=True).to_csv(report / "predictions_partial.csv", index=False)

    # Chuyển miền: tuyệt đối không dùng nhãn XJTU để fit hoặc điều chỉnh cấu hình.
    direct = clone(estimators["Random Forest"]).fit(S, sdu.soh_pct)
    record("SDU to XJTU", "RF normalized", np.arange(len(data)), direct.predict(X), 0)
    frozen = joblib.load(ROOT / "artifacts/random_forest.joblib")
    record("SDU to XJTU", "RF original SDU", np.arange(len(data)), frozen["model"].predict(data[FEATURES]), 0)

    # Kiểm thử đổi chiến lược sạc: giữ riêng toàn bộ batch.
    for batch in (1, 2):
        train = np.flatnonzero(data.batch.to_numpy() != batch)
        test = np.flatnonzero(data.batch.to_numpy() == batch)
        fitted = clone(estimators["Random Forest"]).fit(X.iloc[train], y[train])
        record(f"Held-out batch {batch}", "Random Forest", test, fitted.predict(X.iloc[test]), batch)

    predictions = pd.concat(result, ignore_index=True)
    by_cell = scores(predictions)
    summary = by_cell.groupby(["design", "model"], sort=False)[["mae", "rmse", "r2"]].mean().reset_index()
    predictions.to_csv(report / "predictions.csv", index=False)
    by_cell.to_csv(report / "metrics_by_battery.csv", index=False)
    summary.to_csv(report / "metrics_summary.csv", index=False)
    pd.DataFrame(assignments).to_csv(report / "split_assignments.csv", index=False)
    pd.DataFrame(timings).to_csv(report / "timings.csv", index=False)
    (report / "predictions_partial.csv").unlink(missing_ok=True)
    compared = by_cell[by_cell.design == "XJTU held-out"].pivot(index="battery", columns="model", values="mae")
    paired = (compared["RF multi-source"] - compared["Random Forest"]).rename("mae_multi_minus_single_pp").reset_index()
    paired.to_csv(report / "paired_multi_source.csv", index=False)

    from save_xjtu_models import main as save_app_models
    save_app_models()
    metadata = {"seed": 42, "folds": 5, "model_cycles":len(data), "initial_reference_cycles_not_used":23, "features": TRANSFER_FEATURES,
                "features_sha256": hashlib.sha256((report / "features.csv").read_bytes()).hexdigest(),
                "sdu_features_sha256": hashlib.sha256((ROOT / "reports/features.csv").read_bytes()).hexdigest(),
                "normalization": "current_mean and current_std divided by source nominal Ah, not measured capacity; phase_code removed",
                "soh_definition": "XJTU discharge_capacity_Ah / nominal 2.0 Ah * 100; SDU / nominal 2.4 Ah * 100",
                "evaluation": "5-fold grouped by physical XJTU cell, shuffled seed 42; macro unweighted across 23 cells; fixed settings, no hyperparameter tuning",
                "multi_source": "All SDU + XJTU train cells only per fold; total sample weights 0.5 per source. Test XJTU labels not used in training.",
                "transfer": "Frozen original SDU RF and independently refit RF on SDU normalized features; no XJTU labels used for fit",
                "gru": {"included": not args.skip_gru, "hidden":24, "epochs":20,"sequence_positions":25,"training_scalers_only":True},
                "parameters": {name: model.get_params(deep=False) for name, model in estimators.items()},
                "limitations": "Exploratory multi-source and source-transfer experiments. No real-vehicle BMS, no RUL, no claim of universal performance. App artifacts refit on all training-source cells and are not held-out validation."}
    (report / "run_metadata.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2,default=str)+'\n')
    print(summary.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
