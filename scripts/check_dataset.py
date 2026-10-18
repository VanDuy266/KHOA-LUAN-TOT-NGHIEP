"""Kiểm tra độc lập toàn bộ CSV theo từng khối 100.000 dòng."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = {}
    manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        if not item["name"].endswith(".mat"):
            continue
        path = ROOT / "data/mat" / item["name"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Sai checksum nguồn")
        battery = path.stem
        for index, operation in enumerate(loadmat(path, simplify_cells=True)[battery]["cycle"], 1):
            kind = operation["type"]
            if kind not in ["charge", "discharge"]:
                continue
            signals = operation["data"]
            arrays = {"time": np.asarray(signals["Time"]),
                "terminal_voltage": np.asarray(signals["Voltage_measured"]),
                "terminal_current": np.asarray(signals["Current_measured"]),
                "temperature": np.asarray(signals["Temperature_measured"])}
            valid = np.logical_and.reduce([np.isfinite(values) for values in arrays.values()])
            source[(battery, index)] = {
                "type": kind, "count": int(valid.sum()), "seen": 0,
                **{name: values[valid] for name, values in arrays.items()}}
    counts = {}
    rows = 0
    previous = None
    path = ROOT / "data/clean/measurements_all.csv"
    for chunk in pd.read_csv(path, chunksize=100_000):
        if chunk.isna().any().any():
            raise ValueError("CSV có giá trị thiếu")
        numeric = chunk.select_dtypes(include="number")
        if not np.isfinite(numeric.to_numpy()).all():
            raise ValueError("CSV có số vô hạn")
        keys = pd.MultiIndex.from_frame(chunk[["battery", "operation_index", "time"]])
        if keys.has_duplicates or not keys.is_monotonic_increasing:
            raise ValueError("Khóa trùng hoặc thứ tự sai trong CSV")
        if previous is not None and keys[0] <= previous:
            raise ValueError("Khóa trùng/sai thứ tự ở ranh giới hai khối")
        previous = keys[-1]
        # Đối chiếu từng tín hiệu với mảng MATLAB, không chỉ kiểm đếm dòng.
        for key, group in chunk.groupby(["battery", "operation_index"], sort=False):
            item = source[key]
            start = item["seen"]
            stop = start + len(group)
            if not group.operation_type.eq(item["type"]).all():
                raise ValueError("Loại sạc/xả không khớp nguồn")
            for column in ["time", "terminal_voltage", "terminal_current", "temperature"]:
                if not np.allclose(group[column], item[column][start:stop], rtol=1e-12, atol=1e-12):
                    raise ValueError(f"Tín hiệu {column} không khớp MATLAB: {key}")
            item["seen"] = stop
        for (battery, kind), count in chunk.groupby(["battery", "operation_type"]).size().items():
            counts[(battery, kind)] = counts.get((battery, kind), 0) + int(count)
        rows += len(chunk)
    if any(item["seen"] != item["count"] for item in source.values()):
        raise ValueError("Thiếu bản ghi so với MATLAB")
    if rows < 2_000_000:
        raise ValueError(f"Chưa đủ hai triệu dòng: {rows}")
    feature = pd.read_csv(ROOT / "data/clean/cycle_features.csv")
    if feature.duplicated(["battery", "cycle"]).any() or feature.isna().any().any():
        raise ValueError("Bảng mẫu học máy có khóa trùng hoặc dữ liệu thiếu")
    result = {"status": "passed", "measurement_rows": rows, "minimum_rows": 2_000_000,
        "missing_values": 0, "duplicate_measurement_keys": 0,
        "source_arrays_match": True, "relative_tolerance": 1e-12,
        "feature_rows": len(feature), "independent_batteries": feature.battery.nunique(),
        "per_battery_operation": [{"battery": b, "type": k, "rows": v} for (b, k), v in sorted(counts.items())],
        "csv_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "note": "Over 2M measurements, not 2M independent SOH samples. MAT mirror, not publisher-byte-verified."}
    (ROOT / "reports/dataset_check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
