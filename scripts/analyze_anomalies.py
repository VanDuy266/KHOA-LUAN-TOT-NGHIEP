"""Kiểm thử giữ riêng pin cho Isolation Forest; không có nhãn lỗi thực tế."""

import sys, json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.anomaly import trend_features, COLUMNS, explain


def fit_model(data):
    model = IsolationForest(
        n_estimators=150,
        max_samples=256,
        contamination="auto",
        random_state=42,
        n_jobs=2,
    )
    model.fit(data[COLUMNS])
    scores = -model.score_samples(data[COLUMNS])
    threshold = float(np.quantile(scores, 0.99))
    return model, threshold


def main():
    data = trend_features(pd.read_csv(ROOT / "reports/features.csv"))
    assignments = (
        pd.read_csv(ROOT / "reports/split_assignments.csv")
        .set_index("battery")
        .test_fold
    )
    data["fold"] = data.battery.map(assignments)
    if data.fold.isna().any():
        raise ValueError("Thiếu phân hoạch pin")
    data["iforest_score"] = np.nan
    data["iforest_threshold"] = np.nan
    data["iforest_flag"] = False
    for fold in sorted(data.fold.unique()):
        train = data[data.eligible & (data.fold != fold)]
        index = data.index[data.eligible & (data.fold == fold)]
        assert set(train.battery).isdisjoint(data.loc[index].battery)
        model, threshold = fit_model(train)
        score = -model.score_samples(data.loc[index, COLUMNS])
        data.loc[index, "iforest_score"] = score
        data.loc[index, "iforest_threshold"] = threshold
        data.loc[index, "iforest_flag"] = score > threshold
    data["flag"] = data.rule_flag | data.iforest_flag
    data["reason"] = [explain(row) for row in data.itertuples()]
    data.to_csv(ROOT / "reports/anomaly_predictions.csv", index=False)
    summary = (
        data.groupby("phase")
        .agg(
            cycles=("cycle", "size"),
            eligible=("eligible", "sum"),
            rule_flags=("rule_flag", "sum"),
            iforest_flags=("iforest_flag", "sum"),
            flagged=("flag", "sum"),
        )
        .reset_index()
    )
    summary["flag_rate_pct"] = 100 * summary.flagged / summary.eligible
    summary.to_csv(ROOT / "reports/anomaly_summary.csv", index=False)
    model, threshold = fit_model(data[data.eligible])
    joblib.dump(
        dict(
            model=model,
            threshold=threshold,
            features=COLUMNS,
            window=8,
            min_history=5,
            dataset="SDU",
            scope="Historical measured cycle SOH; not BMS-validated or safety diagnosis",
        ),
        ROOT / "artifacts/anomaly_iforest.joblib",
    )
    metadata = dict(
        method="Past-window robust trend + Isolation Forest",
        window=8,
        min_history=5,
        rule_z=4.5,
        rule_innovation_pp=1.0,
        scale_floor_soh_pp_percycle=0.01,
        iforest_threshold="99th percentile training scores; strict greater-than",
        seed=42,
        validation="Same 5 physical-battery folds; threshold fitted on training pins only",
        target="Observed reference SOH sequence, not predicted SOH or raw BMS signals",
        features=COLUMNS,
        source_sha256=hashlib.sha256(
            (ROOT / "reports/features.csv").read_bytes()
        ).hexdigest(),
        ground_truth_fault_labels=False,
        precision_recall_available=False,
        bms_vehicle_validation=False,
        limitations="Flags for review only; no sensitivity/specificity, fault diagnosis, RUL or vehicle safety claim. Within a held-out pin, previous observations are available to monitoring.",
    )
    (ROOT / "reports/anomaly_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    )
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
