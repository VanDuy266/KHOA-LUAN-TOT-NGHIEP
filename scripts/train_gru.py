"""GRU học chuỗi V/I/T trong 120 giây đầu; cùng phân hoạch pin với mô hình bảng."""

import os

os.environ.setdefault("OMP_NUM_THREADS", "2")
import json
import hashlib
import time
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch import nn
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
torch.set_num_threads(2)


class HealthGRU(nn.Module):
    def __init__(self):
        super().__init__()
        self.gru = nn.GRU(3, 24, batch_first=True)
        self.head = nn.Sequential(nn.Linear(26, 24), nn.ReLU(), nn.Linear(24, 1))

    def forward(self, signals, context):
        _, hidden = self.gru(signals)
        return self.head(torch.cat([hidden[-1], context], dim=1)).squeeze(1)


def sequences(data):
    cache = ROOT / "data/clean/gru_sequences.npz"
    # Bộ nhớ đệm chỉ chứa chuỗi đầu xả dẫn xuất, không thay đổi nguồn.
    if cache.exists():
        stored = np.load(cache)
        if np.array_equal(
            stored["keys"],
            data[["battery", "phase", "cycle"]].astype(str).agg("|".join, axis=1),
        ):
            return stored["signals"]
    lookup = {}
    grid = np.linspace(0, 120, 25)
    for (battery, phase), group in data.groupby(["battery", "phase"]):
        raw = pd.read_parquet(ROOT / "data/clean/cells" / f"{phase}_{battery}.parquet")
        for cycle, part in raw[raw.time <= 120].groupby("cycle"):
            part = part.sort_values("time")
            lookup[(battery, phase, cycle)] = np.column_stack(
                [
                    np.interp(grid, part.time, part[column])
                    for column in [
                        "terminal_voltage",
                        "terminal_current",
                        "temperature",
                    ]
                ]
            )
    signals = np.stack(
        [lookup[(row.battery, row.phase, row.cycle)] for row in data.itertuples()]
    ).astype("float32")
    keys = (
        data[["battery", "phase", "cycle"]]
        .astype(str)
        .agg("|".join, axis=1)
        .to_numpy(dtype=str)
    )
    np.savez_compressed(cache, signals=signals, keys=keys)
    return signals


def fit_predict(signals, context, target, train, test, save_path=None):
    torch.manual_seed(42)
    generator = torch.Generator().manual_seed(42)
    signal_scaler = StandardScaler().fit(signals[train].reshape(-1, 3))
    context_scaler = StandardScaler().fit(context[train])
    target_mean, target_std = target[train].mean(), target[train].std()
    x = torch.tensor(
        signal_scaler.transform(signals.reshape(-1, 3)).reshape(signals.shape),
        dtype=torch.float32,
    )
    c = torch.tensor(context_scaler.transform(context), dtype=torch.float32)
    y = torch.tensor((target - target_mean) / target_std, dtype=torch.float32)
    dataset = torch.utils.data.TensorDataset(x[train], c[train], y[train])
    loader = torch.utils.data.DataLoader(
        dataset, batch_size=256, shuffle=True, generator=generator
    )
    network = HealthGRU()
    optimizer = torch.optim.Adam(network.parameters(), lr=0.002)
    network.train()
    for epoch in range(20):
        for xb, cb, yb in loader:
            optimizer.zero_grad()
            loss = nn.functional.mse_loss(network(xb, cb), yb)
            loss.backward()
            nn.utils.clip_grad_norm_(network.parameters(), 1.0)
            optimizer.step()
    if save_path is not None:
        torch.save(network.state_dict(), save_path)
        config = dict(
            signal_mean=signal_scaler.mean_.tolist(),
            signal_scale=signal_scaler.scale_.tolist(),
            context_mean=context_scaler.mean_.tolist(),
            context_scale=context_scaler.scale_.tolist(),
            target_mean=float(target_mean),
            target_std=float(target_std),
            dataset="SDU",
            training_samples=len(train),
            data_sha256=hashlib.sha256(
                (ROOT / "reports/features.csv").read_bytes()
            ).hexdigest(),
            scope="Refit on full data, not held-out validation",
        )
        save_path.with_suffix(".json").write_text(json.dumps(config, indent=2) + "\n")
    network.eval()
    with torch.no_grad():
        prediction = network(x[test], c[test]).numpy() * target_std + target_mean
    return prediction


def main():
    data = pd.read_csv(ROOT / "reports/features.csv")
    signals = sequences(data)
    context = data[["phase_code", "cycle"]].to_numpy(dtype="float32")
    target = data.soh_pct.to_numpy(dtype="float32")
    split = (
        pd.read_csv(ROOT / "reports/split_assignments.csv")
        .set_index("battery")
        .test_fold
    )
    folds = data.battery.map(split).to_numpy()
    scores, predictions, timings = [], [], []
    for fold in range(1, 6):
        train, test = np.flatnonzero(folds != fold), np.flatnonzero(folds == fold)
        start = time.perf_counter()
        prediction = fit_predict(signals, context, target, train, test)
        timings.append(
            dict(
                model="GRU",
                fold=fold,
                fit_seconds=time.perf_counter() - start,
                predict_seconds=np.nan,
                n_train=len(train),
                n_test=len(test),
            )
        )
        part = data.iloc[test].copy()
        part["predicted_soh"] = prediction
        for battery, group in part.groupby("battery"):
            scores.append(
                dict(
                    model="GRU",
                    fold=fold,
                    held_out_battery=battery,
                    n_train=len(train),
                    n_test=len(group),
                    mae=mean_absolute_error(group.soh_pct, group.predicted_soh),
                    rmse=root_mean_squared_error(group.soh_pct, group.predicted_soh),
                    r2=r2_score(group.soh_pct, group.predicted_soh),
                )
            )
        predictions.append(
            part[["battery", "phase", "cycle", "soh_pct", "predicted_soh"]]
            .rename(columns={"soh_pct": "actual_soh"})
            .assign(model="GRU", fold=fold)
        )
        print(f"GRU: vòng {fold}/5, {time.perf_counter()-start:.1f} giây", flush=True)
    for filename, extra in [
        ("metrics_by_battery.csv", pd.DataFrame(scores)),
        ("predictions.csv", pd.concat(predictions)),
        ("timings.csv", pd.DataFrame(timings)),
    ]:
        old = pd.read_csv(ROOT / "reports" / filename)
        pd.concat([old[old.model != "GRU"], extra], ignore_index=True).to_csv(
            ROOT / "reports" / filename, index=False
        )
    all_scores = pd.read_csv(ROOT / "reports/metrics_by_battery.csv")
    all_scores.groupby("model", sort=False)[
        ["mae", "rmse", "r2"]
    ].mean().reset_index().to_csv(ROOT / "reports/metrics_summary.csv", index=False)
    pred = pd.read_csv(ROOT / "reports/predictions.csv")
    phase_scores = []
    for (name, phase), part in pred.groupby(["model", "phase"]):
        phase_scores.append(
            dict(
                model=name,
                phase=phase,
                n_test=len(part),
                mae=mean_absolute_error(part.actual_soh, part.predicted_soh),
                rmse=root_mean_squared_error(part.actual_soh, part.predicted_soh),
                r2=r2_score(part.actual_soh, part.predicted_soh),
            )
        )
    pd.DataFrame(phase_scores).to_csv(
        ROOT / "reports/metrics_by_phase.csv", index=False
    )
    metadata = dict(
        model="GRU",
        torch=torch.__version__,
        seed=42,
        epochs=20,
        batch_size=256,
        hidden_units=24,
        sequence_length=25,
        signals=["voltage", "current", "temperature"],
        context=["phase_code", "cycle"],
        window_seconds=120,
        learning_rate=0.002,
        preprocessing="25 equally spaced positions within first 120 seconds; linear interpolation with nearest endpoint at boundaries; training-fold scalers only; source CSV unchanged",
        comparison="Same 5 physical-battery folds as tabular models. Different representation, not an isolated algorithm comparison.",
        timing="fit_seconds includes fold preprocessing, training and inference; predict_seconds not measured separately",
    )
    (ROOT / "reports/gru_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    summary = pd.read_csv(ROOT / "reports/metrics_summary.csv")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(summary.model, summary.mae)
    ax.set(
        ylabel="MAE (percentage points SOH)",
        title="SDU: 5-fold grouped by physical battery",
    )
    fig.tight_layout()
    fig.savefig(ROOT / "reports/model_comparison.png", dpi=180)
    plt.close(fig)
    # Bản học lại toàn bộ dùng cho bàn giao; không dùng để báo cáo chỉ số kiểm thử.
    indexes = np.arange(len(data))
    fit_predict(
        signals, context, target, indexes, indexes[:1], ROOT / "artifacts/gru.pt"
    )
    print(summary.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
