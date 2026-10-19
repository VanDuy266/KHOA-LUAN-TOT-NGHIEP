"""Kiểm tra bỏ nhóm đặc trưng và dự đoán phần cuối chu kỳ trên SDU."""

import os

os.environ.setdefault("OMP_NUM_THREADS", "2")
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from run_experiment import models
from battery_soh.features import FEATURES

ROOT = Path(__file__).resolve().parents[1]


def main():
    data = pd.read_csv(ROOT / "reports/features.csv")
    scores = []
    for configuration, columns in {
        "Without cycle": [x for x in FEATURES if x != "cycle"],
        "Without phase": [x for x in FEATURES if x != "phase_code"],
        "Voltage only": [x for x in FEATURES if x.startswith("voltage")],
    }.items():
        for fold, (train, test) in enumerate(
            GroupKFold(n_splits=5, shuffle=True, random_state=42).split(
                data, groups=data.battery
            ),
            1,
        ):
            model = models()["Random Forest"][0]
            model.fit(data.iloc[train][columns], data.iloc[train].soh_pct)
            part = data.iloc[test].copy()
            part["prediction"] = model.predict(part[columns])
            for battery, group in part.groupby("battery"):
                scores.append(
                    dict(
                        configuration=configuration,
                        battery=battery,
                        fold=fold,
                        mae=mean_absolute_error(group.soh_pct, group.prediction),
                        rmse=root_mean_squared_error(group.soh_pct, group.prediction),
                    )
                )
            print(configuration, fold, "/5", flush=True)
    baseline = pd.read_csv(ROOT / "reports/metrics_by_battery.csv").query(
        "model == 'Random Forest'"
    )
    scores.extend(
        dict(
            configuration="Full features",
            battery=r.held_out_battery,
            fold=r.fold,
            mae=r.mae,
            rmse=r.rmse,
        )
        for r in baseline.itertuples()
    )
    ablation = pd.DataFrame(scores)
    ablation.to_csv(ROOT / "reports/ablation_by_battery.csv", index=False)
    ablation.groupby("configuration", sort=False)[
        ["mae", "rmse"]
    ].mean().reset_index().to_csv(ROOT / "reports/ablation_summary.csv", index=False)
    trains, tests, cutoffs = [], [], {}
    for (battery, phase), part in data.groupby(["battery", "phase"]):
        part = part.sort_values("cycle")
        cut = int(len(part) * 0.7)
        train, test = part.iloc[:cut], part.iloc[cut:]
        trains.append(train)
        tests.append(test)
        cutoffs[battery + "|" + phase] = dict(
            n_train=len(train),
            n_test=len(test),
            last_train_cycle=int(train.cycle.max()),
            first_test_cycle=int(test.cycle.min()),
            last_soh=float(train.soh_pct.iloc[-1]),
        )
    train, test = pd.concat(trains), pd.concat(tests)
    forest = models()["Random Forest"][0]
    forest.fit(train[FEATURES], train.soh_pct)
    test = test.copy()
    test["prediction"] = forest.predict(test[FEATURES])
    temporal = []
    predictions = []
    for (battery, phase), part in test.groupby(["battery", "phase"]):
        cut = cutoffs[battery + "|" + phase]
        for name, predicted in {
            "Random Forest": part.prediction.to_numpy(),
            "Last known SOH": np.repeat(cut["last_soh"], len(part)),
        }.items():
            temporal.append(
                dict(
                    battery=battery,
                    phase=phase,
                    model=name,
                    **cut,
                    mae=mean_absolute_error(part.soh_pct, predicted),
                    rmse=root_mean_squared_error(part.soh_pct, predicted)
                )
            )
            predictions.extend(
                dict(
                    battery=battery,
                    phase=phase,
                    cycle=int(c),
                    model=name,
                    actual_soh=float(y),
                    predicted_soh=float(p),
                )
                for c, y, p in zip(part.cycle, part.soh_pct, predicted)
            )
    pd.DataFrame(temporal).to_csv(ROOT / "reports/temporal_metrics.csv", index=False)
    pd.DataFrame(predictions).to_csv(
        ROOT / "reports/temporal_predictions.csv", index=False
    )
    (ROOT / "reports/temporal_design.json").write_text(
        json.dumps(
            dict(
                design="Pooled first 70% cycles within each battery and phase for training; remaining 30% for test",
                training_cycles=len(train),
                test_cycles=len(test),
                cutoffs=cutoffs,
            ),
            indent=2,
        )
    )
    print(
        "Đã hoàn thành kiểm thử theo nhóm pin, bỏ đặc trưng và theo thời gian.",
        flush=True,
    )


if __name__ == "__main__":
    main()
