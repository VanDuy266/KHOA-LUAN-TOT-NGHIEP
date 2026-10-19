"""Chiếu dữ liệu SDU sang Parquet theo pin/giai đoạn, giữ ZIP nguồn nguyên vẹn."""

import hashlib, json, sys, shutil
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.features import FEATURES, extract_window


def main():
    source = Path((ROOT / "data/source/location.txt").read_text().strip())
    folder = ROOT / "data/clean"
    cells = folder / "cells"
    cells.mkdir(parents=True, exist_ok=True)
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    original = pd.read_csv(source / "cycle_features.csv")
    original["battery"] = original.battery.map(lambda x: f"SDU_{int(x):02d}")
    original.to_csv(folder / "cycle_features.csv", index=False)
    original.to_csv(reports / "features.csv", index=False)
    records = pd.read_csv(source / "source_preservation_audit.csv")
    audit = []
    samples = []
    mismatches = 0
    for n, row in enumerate(records.itertuples(), 1):
        import gzip

        with gzip.open(source / row.output, "rb") as f:
            digest = hashlib.sha256()
            for block in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != row.uncompressed_sha256:
            raise ValueError("SHA-256 sai: " + row.output)
        raw = pd.read_csv(source / row.output)
        battery = f"SDU_{int(row.battery):02d}"
        phase = row.phase
        expected = original[
            (original.battery == battery) & (original.phase == phase)
        ].set_index("cycle")
        raw = raw.rename(
            columns={
                "Cycle_Index": "cycle",
                "Test_Time(s)": "time",
                "Voltage(V)": "terminal_voltage",
                "Current(A)": "terminal_current",
                "Aux_Temperature_1(C)": "temperature",
            }
        )
        data = raw[
            ["cycle", "time", "terminal_voltage", "terminal_current", "temperature"]
        ].copy()
        data["battery"] = battery
        data["phase"] = phase
        data["phase_code"] = 0 if phase == "primary" else 1
        data = data.sort_values(["cycle", "time"])
        data["time"] -= data.groupby("cycle").time.transform("min")
        data["capacity"] = data.cycle.map(expected.capacity_ah)
        data["SOH"] = data.capacity / 2.4
        path = cells / f"{phase}_{battery}.parquet"
        with pq.ParquetWriter(
            path,
            pa.Table.from_pandas(data.iloc[:1], preserve_index=False).schema,
            compression="zstd",
        ) as writer:
            for cycle, part in data.groupby("cycle", sort=True):
                values = extract_window(part, int(cycle))
                truth = expected.loc[cycle]
                mismatches += int(
                    not all(
                        np.isclose(values[key], truth[key], atol=1e-10, rtol=1e-10)
                        for key in FEATURES
                        if key != "cycle"
                    )
                )
                writer.write_table(pa.Table.from_pandas(part, preserve_index=False))
                if battery == "SDU_01" and phase == "primary" and len(samples) < 3:
                    samples.append(part.loc[part.time <= 120].copy())
        audit.append(
            dict(
                battery=battery,
                phase=phase,
                rows_before=len(data),
                all_rows=len(data),
                cycles=data.cycle.nunique(),
                missing_values=int(data.isna().sum().sum()),
                nominal_capacity_ah=2.4,
            )
        )
        print(f"SDU {n}/172: {battery} {phase}, {len(data):,} dòng", flush=True)
    if mismatches:
        raise ValueError("Đặc trưng không khớp bộ nguồn: " + str(mismatches))
    pd.concat(samples).to_csv(folder / "sample_measurements.csv", index=False)
    pd.DataFrame(audit).to_csv(reports / "data_audit.csv", index=False)
    original[["battery", "phase", "cycle", "capacity_ah", "soh_pct"]].to_csv(
        folder / "cycle_labels.csv", index=False
    )
    verification = json.loads((source / "verification/summary.json").read_text())
    source_info = json.loads((source / "dataset_summary.json").read_text())
    summary = dict(
        dataset="SDU",
        source="https://zenodo.org/records/14859405",
        source_doi="10.5281/zenodo.14859405",
        original_year=2025,
        battery_count=86,
        all_measurement_rows=sum(r["all_rows"] for r in audit),
        measurement_rows=sum(r["all_rows"] for r in audit),
        feature_rows=len(original),
        discharge_cycles=len(original),
        nominal_capacity_ah=2.4,
        window_seconds=120,
        features=FEATURES,
        missing_values=0,
        duplicates_removed=0,
        invalid_rows_removed=0,
        excluded_cycles=0,
        source_parent_rows=30929675,
        sampling_method=source_info["sampling_method"],
        source_original_rows=145112317,
        suspected_points=verification["retained_parent_spike_candidates"],
        suspected_points_in_window=verification["spike_candidates_first120s"],
        source_backward_steps=verification["backward_time_steps"],
        phases={"primary": "Sử dụng ban đầu", "second_life": "Tái sử dụng"},
        country="China; laboratory cells, not Vietnam vehicle packs",
    )
    if (
        summary["all_measurement_rows"] != source_info["measurement_rows"]
        or len(original) != 20823
    ):
        raise ValueError("Sai quy mô SDU")
    (reports / "dataset_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    shutil.copy2(
        source / "verification/retained_spike_candidates.csv",
        reports / "suspected_measurements.csv",
    )
    source_text = (source / "NGUON_DU_LIEU.md").read_text()
    (ROOT / "data/README.md").write_text(
        "\n".join(
            line
            for line in source_text.splitlines()
            if not line.startswith("Trong báo cáo có thể ghi:")
        )
        + "\n"
    )
    quality = (
        (source / "KET_QUA_KIEM_TRA.md")
        .read_text()
        .replace(
            "Các kiểm tra này chưa đánh giá chất lượng dự đoán; cần huấn luyện và kiểm thử bốn cấu hình đã chọn. Chưa cập nhật dataset này vào ứng dụng.",
            "Kiểm tra dữ liệu tách biệt với đánh giá mô hình. Kết quả thực nghiệm nằm trong reports/ sau khi chạy các bước huấn luyện.",
        )
    )
    (ROOT / "data/KIEM_TRA_DU_LIEU.md").write_text(quality)
    (reports / "excluded_cycles.csv").write_text("battery,phase,cycle,reason\n")
    (reports / "removed_measurements.csv").write_text("battery,phase,cycle,reason\n")
    example = pd.concat(samples).query("cycle == 1")
    (ROOT / "examples").mkdir(exist_ok=True)
    for p in (ROOT / "examples").glob("*B0005*"):
        p.unlink()
    example.to_csv(ROOT / "examples/chu_ky_mau_SDU.csv", index=False)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
