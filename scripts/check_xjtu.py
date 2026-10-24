"""Đối chiếu khóa, nhãn, phân hoạch và chỉ số với các dự đoán đã lưu."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / "reports/xjtu"
    data = pd.read_csv(folder / "features.csv")
    summary = json.loads((folder / "dataset_summary.json").read_text())
    run = json.loads((folder / "run_metadata.json").read_text())
    assert hashlib.sha256((folder / "features.csv").read_bytes()).hexdigest() == run["features_sha256"] == summary["features_sha256"]
    assert hashlib.sha256((ROOT / "reports/features.csv").read_bytes()).hexdigest() == run["sdu_features_sha256"]
    assert data.battery.nunique() == 23 and len(data) == summary["valid_cycles"]
    assert not data.duplicated(["battery", "cycle"]).any()
    assert np.allclose(data.soh_pct, data.capacity_ah / 2 * 100)
    modeled = data.loc[data.cycle > 1]
    split = pd.read_csv(folder / "split_assignments.csv")
    assert split.battery.nunique() == 23 and not split.battery.duplicated().any()
    pred = pd.read_csv(folder / "predictions.csv")
    expected_keys = set(zip(modeled.battery, modeled.cycle))
    for (design, _), part in pred.groupby(["design", "model"]):
        assert not part.duplicated(["battery", "cycle"]).any()
        if design in ("XJTU held-out", "SDU to XJTU"):
            assert set(zip(part.battery, part.cycle)) == expected_keys
        if design == "XJTU held-out":
            compared = part.merge(split, on="battery", validate="many_to_one")
            assert (compared.fold == compared.test_fold).all()
    metrics = pd.read_csv(folder / "metrics_summary.csv")
    for row in metrics.itertuples():
        part = pred[(pred.design == row.design) & (pred.model == row.model)].copy()
        part["abs_error"] = abs(part.predicted_soh - part.actual_soh)
        part["squared_error"] = (part.predicted_soh - part.actual_soh) ** 2
        per_pin = part.groupby("battery")[["abs_error", "squared_error"]].mean()
        assert np.isclose(per_pin.abs_error.mean(), row.mae)
        assert np.isclose(np.sqrt(per_pin.squared_error).mean(), row.rmse)
    result = {"status":"passed", "batteries":23, "source_cycles":len(data), "model_cycles":len(modeled),
              "group_folds":5, "held_out_models":pred.loc[pred.design == "XJTU held-out", "model"].nunique(),
              "macro_metrics_recomputed":True, "label_ratio_verified":True, "sdu_inputs_hash_unchanged":True,
              "scope":"Prepared tables, stored folds and all saved predictions checked; does not certify absence of sensor noise or vehicle validity."}
    (folder / "verification.json").write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == "__main__":main()
