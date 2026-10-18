"""Đọc MATLAB bằng scipy, xuất CSV sạch và đặc trưng cho bài toán SOH.

Chạy: python scripts/prepare_data.py
Giữ dữ liệu đo thật. Không nội suy, không nhân bản, không cắt SOH về 100%.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.features import extract_window, validate_target

SIGNALS = ["time", "terminal_voltage", "terminal_current", "temperature"]
FULL_COLUMNS = ["battery", "operation_type", "operation_index", "cycle",
                *SIGNALS, "ambient_temperature"]


def read_battery(path):
    """Một operation là một lần sạc, xả hoặc đo trở kháng trong MATLAB."""
    battery = path.stem
    operations = loadmat(path, simplify_cells=True)[battery]["cycle"]
    frames = []
    counters = {"charge": 0, "discharge": 0}
    for operation_number, operation in enumerate(operations, start=1):
        kind = operation["type"]
        if kind not in counters:
            continue  # Trở kháng có cấu trúc khác, không ghép vào bảng tín hiệu.
        counters[kind] += 1
        signals = operation["data"]
        frame = pd.DataFrame({
            "time": signals["Time"],
            "terminal_voltage": signals["Voltage_measured"],
            "terminal_current": signals["Current_measured"],
            "temperature": signals["Temperature_measured"],
        })
        frame["battery"] = battery
        frame["operation_type"] = kind
        frame["operation_index"] = operation_number
        frame["cycle"] = counters[kind]
        frame["ambient_temperature"] = float(operation["ambient_temperature"])
        # Chỉ chu kỳ xả có nhãn dung lượng. Không gán nhãn tương lai cho sạc.
        frame["capacity"] = float(signals["Capacity"]) if kind == "discharge" else np.nan
        frame["SOH"] = frame["capacity"] / 2.0
        frames.append(frame)
    if not frames:
        raise ValueError(f"{battery}: không có chu kỳ sạc/xả")
    return pd.concat(frames, ignore_index=True)


def clean_battery(frame):
    """Xác minh tính nhất quán, chỉ loại dòng trùng toàn bộ nếu có."""
    numeric = [*SIGNALS, "ambient_temperature"]
    valid = np.isfinite(frame[numeric].to_numpy()).all(axis=1)
    # Nguồn B0018 có hai bản ghi sạc thiếu cả ba tín hiệu đo.
    # Loại bản ghi không sử dụng được, không nội suy để bù số lượng.
    frame = frame.loc[valid].copy()
    if (frame.time < 0).any():
        raise ValueError("Có thời gian âm")
    cleaned = frame.drop_duplicates().copy()
    if cleaned.duplicated(["battery", "operation_index", "time"]).any():
        raise ValueError("Một thời điểm trong cùng operation có tín hiệu xung đột")
    return cleaned.sort_values(["battery", "operation_index", "time"]).reset_index(drop=True)


def main():
    manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
    folder = ROOT / "data/clean"
    folder.mkdir(parents=True, exist_ok=True)
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    discharge_frames, features, audit, excluded, removed = [], [], [], [], []
    full_path = folder / "measurements_all.csv"
    temporary = full_path.with_suffix(".tmp")
    first_battery = True
    for item in manifest["files"]:
        if not item["name"].endswith(".mat"):
            continue
        path = ROOT / "data/mat" / item["name"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Sai checksum: " + path.name)
        original = read_battery(path)
        valid = np.isfinite(original[[*SIGNALS, "ambient_temperature"]].to_numpy()).all(axis=1)
        for record in original.loc[~valid, ["battery", "operation_type", "operation_index", "cycle", "time"]].to_dict("records"):
            removed.append({**record, "reason": "Missing or non-finite measured signals"})
        cleaned = clean_battery(original)
        # Ghi từng pin để không phải giữ 2 triệu dòng trong RAM cùng lúc.
        cleaned[FULL_COLUMNS].to_csv(temporary, mode="w" if first_battery else "a",
                                    header=first_battery, index=False)
        first_battery = False
        discharge = cleaned[cleaned.operation_type == "discharge"].copy()
        discharge_frames.append(discharge)
        battery = path.stem
        audit.append({"battery": battery, "rows_before": len(original), "all_rows": len(cleaned),
            "charge_rows": int((cleaned.operation_type == "charge").sum()), "rows": len(discharge),
            "invalid_rows_removed": int((~valid).sum()),
            "duplicates_removed": int(valid.sum()) - len(cleaned),
            "missing_values": int(cleaned[FULL_COLUMNS].isna().sum().sum()),
            "charge_cycles": int(cleaned[cleaned.operation_type == "charge"].cycle.nunique()),
            "cycles": discharge.cycle.nunique(), "min_soh_pct": discharge.SOH.min() * 100,
            "max_soh_pct": discharge.SOH.max() * 100})
        for cycle, group in discharge.groupby("cycle"):
            target = validate_target(group)
            try:
                values = extract_window(group, cycle)
                features.append({"battery": battery, "soh_pct": target, **values})
            except ValueError as error:
                excluded.append({"battery": battery, "cycle": int(cycle), "reason": str(error)})
    if first_battery:
        raise ValueError("Manifest không có file MATLAB")
    temporary.replace(full_path)
    data = pd.concat(discharge_frames, ignore_index=True)
    data = data[[*FULL_COLUMNS, "capacity", "SOH"]]
    feature_frame = pd.DataFrame(features)
    data.to_csv(folder / "measurements.csv", index=False)
    feature_frame.to_csv(folder / "cycle_features.csv", index=False)
    feature_frame.to_csv(reports / "features.csv", index=False)
    pd.DataFrame(audit).to_csv(reports / "data_audit.csv", index=False)
    pd.DataFrame(excluded, columns=["battery", "cycle", "reason"]).to_csv(reports / "excluded_cycles.csv", index=False)
    pd.DataFrame(removed).to_csv(reports / "removed_measurements.csv", index=False)
    summary = {"source": manifest["repository"], "commit": manifest["commit"],
        "country": "United States (NASA); not Vietnam", "battery_count": data.battery.nunique(),
        "all_measurement_rows": sum(row["all_rows"] for row in audit),
        "charge_rows": sum(row["charge_rows"] for row in audit), "measurement_rows": len(data),
        "discharge_cycles": int(data.groupby("battery").cycle.nunique().sum()),
        "feature_rows": len(feature_frame), "excluded_cycles": len(excluded),
        "missing_values": sum(row["missing_values"] for row in audit),
        "duplicates_removed": sum(row["duplicates_removed"] for row in audit),
        "invalid_rows_removed": sum(row["invalid_rows_removed"] for row in audit),
        "nominal_capacity_ah": 2.0, "soh_above_100_cycle_count": int((feature_frame.soh_pct > 100).sum()),
        "notes": "All signals: charge+discharge. SOH labels: discharge only. MAT mirror; publisher S3 bytes not verified."}
    (reports / "dataset_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(pd.DataFrame(audit).to_string(index=False))
    print(f"Đã xuất {summary['all_measurement_rows']:,} dòng sạc/xả; {len(feature_frame):,} mẫu SOH")


if __name__ == "__main__":
    main()
