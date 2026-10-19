"""Kiểm tra các mô hình bàn giao có thể nạp và dự đoán với dữ liệu SDU."""

import json
import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def test_saved_tabular_models_load_and_predict():
    data = pd.read_csv(ROOT / "reports/features.csv").head(10)
    for name in ["mean_baseline", "ridge", "random_forest", "lightgbm"]:
        artifact = joblib.load(ROOT / "artifacts" / f"{name}.joblib")
        assert artifact["dataset"] == "SDU" and artifact["nominal_capacity_ah"] == 2.4
        assert len(artifact["batteries"]) == 86
        assert np.isfinite(artifact["model"].predict(data[artifact["features"]])).all()


def test_saved_gru_weights_and_scalers_produce_finite_output():
    import torch
    from train_gru import HealthGRU

    data = pd.read_csv(ROOT / "reports/features.csv")
    stored = np.load(ROOT / "data/clean/gru_sequences.npz")
    keys = data[["battery", "phase", "cycle"]].astype(str).agg("|".join, axis=1)
    assert np.array_equal(stored["keys"], keys)
    config = json.loads((ROOT / "artifacts/gru.json").read_text())
    assert config["dataset"] == "SDU" and config["training_samples"] == 20823
    x = (stored["signals"][:4] - np.array(config["signal_mean"])) / np.array(
        config["signal_scale"]
    )
    context = (
        data[["phase_code", "cycle"]].head(4).to_numpy()
        - np.array(config["context_mean"])
    ) / np.array(config["context_scale"])
    model = HealthGRU()
    model.load_state_dict(
        torch.load(ROOT / "artifacts/gru.pt", weights_only=True, map_location="cpu")
    )
    model.eval()
    with torch.no_grad():
        predicted = (
            model(
                torch.tensor(x, dtype=torch.float32),
                torch.tensor(context, dtype=torch.float32),
            ).numpy()
            * config["target_std"]
            + config["target_mean"]
        )
    assert predicted.shape == (4,) and np.isfinite(predicted).all()
