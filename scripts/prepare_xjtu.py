"""Trích xuất XJTU từng pin, giữ dữ liệu và kết quả riêng với SDU."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.xjtu import read_cell


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "data/xjtu/raw")
    args = parser.parse_args()
    output = ROOT / "reports/xjtu"
    clean = ROOT / "data/xjtu/processed"
    output.mkdir(parents=True, exist_ok=True)
    clean.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((args.source.parent / "source_manifest.json").read_text())
    frames, sequences, audits, exclusions = [], [], [], []
    for entry in manifest["files"]:
        path = args.source / entry["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"Nguồn thay đổi: {path}")
        batch = int(path.parent.name.split("-")[1])
        number = int(path.stem.split("-")[-1])
        battery = f"XJTU_B{batch}_{number:02d}"
        frame, seq, windows, rejected, audit = read_cell(path, battery, batch)
        frames.append(frame)
        sequences.append(seq)
        audits.append(audit)
        exclusions.extend(rejected)
        if windows:
            pd.concat(windows, ignore_index=True).to_csv(clean / f"{battery}_windows.csv.gz", index=False)
        print(f"{battery}: {audit['valid_cycles']}/{audit['source_cycles']} chu kỳ", flush=True)
    data = pd.concat(frames, ignore_index=True)
    if data.battery.nunique() != 23 or data.duplicated(["battery", "cycle"]).any():
        raise ValueError("Sai số pin hoặc trùng khóa chu kỳ")
    data.to_csv(output / "features.csv", index=False)
    pd.DataFrame(audits).to_csv(output / "data_audit.csv", index=False)
    pd.DataFrame(exclusions, columns=["battery", "batch", "cycle", "reason"]).to_csv(output / "excluded_cycles.csv", index=False)
    np.savez_compressed(clean / "sequences.npz", signals=np.concatenate(sequences),
                        keys=data[["battery", "cycle"]].astype(str).agg("|".join, axis=1).to_numpy(dtype=str))
    summary = {"dataset": "XJTU Batch-1/2", "source": manifest["source"], "license": manifest["license"],
               "batteries": 23, "available_source_batteries": 55, "selected_batches": [1, 2],
               "raw_points": sum(a["raw_points"] for a in audits), "source_cycles": sum(a["source_cycles"] for a in audits),
               "valid_cycles": len(data), "excluded_cycles": len(exclusions), "nominal_capacity_ah": 2.0,
               "soh_definition": "summary.discharge_capacity_Ah / 2.0 * 100; no clipping",
               "window_seconds": 120, "time_policy": "system_time; duplicate seconds averaged only in derived window",
               "duplicate_window_seconds_aggregated": sum(a["duplicate_window_seconds_aggregated"] for a in audits),
               "features_sha256": hashlib.sha256((output / "features.csv").read_bytes()).hexdigest(),
               "scope": "Laboratory Lishen 18650 NCM; fixed-protocol Batch-1/2 selected before evaluation. Not vehicle BMS. Raw MAT preserved."}
    (output / "dataset_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    (output / "source_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
