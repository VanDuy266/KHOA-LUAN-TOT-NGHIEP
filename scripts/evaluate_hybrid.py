"""Kiểm chứng phương án phần dư trên đúng phân hoạch pin đã công bố."""

import json, sys, time, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.hybrid import RidgeResidualForest
from battery_soh.features import FEATURES

NAME = "Ridge-RF residual"


def main():
    data = pd.read_csv(ROOT / "reports/features.csv")
    split = (
        pd.read_csv(ROOT / "reports/split_assignments.csv")
        .set_index("battery")
        .test_fold
    )
    folds = data.battery.map(split)
    predictions = []
    scores = []
    timings = []
    for fold in sorted(folds.unique()):
        train = data[folds != fold]
        test = data[folds == fold]
        assert set(train.battery).isdisjoint(test.battery)
        model = RidgeResidualForest()
        start = time.perf_counter()
        model.fit(train[FEATURES], train.soh_pct)
        elapsed = time.perf_counter() - start
        tested = (
            test[["battery", "phase", "cycle", "soh_pct"]]
            .rename(columns={"soh_pct": "actual_soh"})
            .copy()
        )
        tested["predicted_soh"] = model.predict(test[FEATURES])
        tested["fold"] = int(fold)
        tested["model"] = NAME
        predictions.append(tested)
        timings.append(dict(fold=int(fold), fit_seconds=elapsed))
        for pin, part in tested.groupby("battery"):
            scores.append(
                dict(
                    model=NAME,
                    fold=int(fold),
                    held_out_battery=pin,
                    n_test=len(part),
                    mae=mean_absolute_error(part.actual_soh, part.predicted_soh),
                    rmse=root_mean_squared_error(part.actual_soh, part.predicted_soh),
                    r2=r2_score(part.actual_soh, part.predicted_soh),
                )
            )
        print("Ridge–RF: vòng", fold, "/5", flush=True)
    pred = pd.concat(predictions, ignore_index=True)
    scores = pd.DataFrame(scores)
    scores.to_csv(ROOT / "reports/hybrid_by_battery.csv", index=False)
    pred.to_csv(ROOT / "reports/hybrid_predictions.csv", index=False)
    result = scores.groupby("model")[["mae", "rmse", "r2"]].mean().reset_index()
    baseline = pd.read_csv(ROOT / "reports/metrics_summary.csv")
    pd.concat([baseline, result], ignore_index=True).to_csv(
        ROOT / "reports/hybrid_comparison.csv", index=False
    )
    # So sánh cặp trên cùng pin; không chọn tham số bằng các điểm kiểm thử này.
    old = pd.read_csv(ROOT / "reports/metrics_by_battery.csv").query(
        "model == 'Random Forest'"
    )
    paired = scores.merge(
        old[["held_out_battery", "mae"]],
        on="held_out_battery",
        suffixes=("_hybrid", "_rf"),
        validate="one_to_one",
    )
    paired["mae_difference"] = paired.mae_hybrid - paired.mae_rf
    paired.to_csv(ROOT / "reports/hybrid_paired_comparison.csv", index=False)
    model = RidgeResidualForest().fit(data[FEATURES], data.soh_pct)
    joblib.dump(
        dict(
            model=model,
            features=FEATURES,
            dataset="SDU",
            nominal_capacity_ah=2.4,
            window_seconds=120,
            batteries=sorted(data.battery.unique()),
            training_min=data[FEATURES].min().to_dict(),
            training_max=data[FEATURES].max().to_dict(),
        ),
        ROOT / "artifacts/ridge_residual_forest.joblib",
    )
    metadata = dict(
        method=NAME,
        formula="SOH = Ridge(X) + RandomForest(X; residual_train)",
        parameters=model.get_params(),
        forest_parameters=model.correction_.get_params(),
        features=FEATURES,
        validation="Same 5 physical battery folds; Ridge/scaler and residual forest fitted only on training pins",
        data_sha256=hashlib.sha256(
            (ROOT / "reports/features.csv").read_bytes()
        ).hexdigest(),
        novelty="Project-specific evaluated combination of existing algorithms; no claim of a novel algorithm or first publication",
        improved_pins=int((paired.mae_difference < 0).sum()),
        total_pins=len(paired),
        mean_mae_difference_vs_rf=float(paired.mae_difference.mean()),
        timings=timings,
    )
    (ROOT / "reports/hybrid_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )
    print(result.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
