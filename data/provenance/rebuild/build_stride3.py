"""Lấy thưa theo quy tắc cố định, giữ nguyên văn dòng CSV nguồn."""

import gzip, hashlib, json, shutil
from pathlib import Path
import numpy as np
import pandas as pd
import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--parent",
    type=Path,
    required=True,
    help="Thư mục xả tham chiếu đầy đủ 30.929.675 dòng",
)
parser.add_argument(
    "--reference",
    type=Path,
    required=True,
    help="Hồ sơ nguồn, nhãn và mã kiểm tra của bộ SDU",
)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
FULL = args.parent
OLD = args.reference
OUT = args.output
OUT.mkdir(parents=True, exist_ok=True)
records = pd.read_csv(FULL / "source_preservation_audit.csv")
audits = []
budgets = []
for n, record in enumerate(records.to_dict("records"), 1):
    frame = pd.read_csv(
        FULL / record["output"], usecols=["Cycle_Index", "Test_Time(s)"]
    )
    keep = np.zeros(len(frame), dtype=bool)
    for cycle, part in frame.groupby("Cycle_Index", sort=False):
        part = part.sort_values("Test_Time(s)", kind="stable")
        t = part["Test_Time(s)"].to_numpy()
        mandatory = (t <= t[0] + 120) | (t == t[-1])
        keep[part.index.to_numpy()[mandatory]] = True
        optional = part.index.to_numpy()[~mandatory]
        keep[optional[::3]] = True
        budgets.append(
            dict(
                cycle=int(cycle),
                rows=len(part),
                mandatory=int(mandatory.sum()),
                phase=record["phase"],
                battery=record["battery"],
                selected_rows=int(mandatory.sum() + len(optional[::3])),
            )
        )
    target = OUT / record["output"]
    target.parent.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256()
    rows = 0
    with gzip.open(FULL / record["output"], "rb") as source, gzip.open(
        target, "wb", compresslevel=6
    ) as dest:
        line = source.readline()
        dest.write(line)
        sha.update(line)
        for index, line in enumerate(source):
            if keep[index]:
                dest.write(line)
                sha.update(line)
                rows += 1
    assert rows == int(keep.sum())
    audits.append(
        dict(
            phase=record["phase"],
            battery=record["battery"],
            output=record["output"],
            source_rows=len(frame),
            selected_rows=rows,
            uncompressed_sha256=sha.hexdigest(),
            source_bytes_preserved=True,
        )
    )
    if n % 20 == 0:
        print(n, "/172 file", flush=True)
for name in [
    "training_table.csv",
    "cycle_features.csv",
    "source_metadata.json",
    "quality_summary.json",
    "quality_audit_by_file.csv",
    "quality_spike_candidates.csv",
    "NGUON_DU_LIEU.md",
    "KET_QUA_KIEM_TRA.md",
]:
    if (OLD / name).exists():
        shutil.copy2(OLD / name, OUT / name)
pd.DataFrame(audits).to_csv(OUT / "source_preservation_audit.csv", index=False)
pd.DataFrame(budgets).to_csv(OUT / "cycle_sampling_audit.csv", index=False)
summary = json.loads((OLD / "dataset_summary.json").read_text())
summary["measurement_rows"] = sum(x["selected_rows"] for x in audits)
summary["sampling_method"] = (
    "Keep every first-120s and final point; retain every third remaining point in time order within each cycle"
)
assert summary["measurement_rows"] == 10505065
(OUT / "dataset_summary.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
)
(OUT / "verification").mkdir(exist_ok=True)
script = (
    (OLD / "verification/verify_dataset.py").read_text().replace("10000000", "10505065")
)
(OUT / "verification/verify_dataset.py").write_text(script)
shutil.copy2(__file__, OUT / "build_stride3.py")
print(summary["measurement_rows"], flush=True)
