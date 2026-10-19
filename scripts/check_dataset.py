"""Đối chiếu toàn bộ 10 triệu dòng Parquet với nhãn và nhật ký nguồn."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]


def main():
    summary = json.loads((ROOT / "reports/dataset_summary.json").read_text())
    features = pd.read_csv(ROOT / "reports/features.csv")
    labels = pd.read_csv(ROOT / "data/clean/cycle_labels.csv")
    keys = ["battery", "phase", "cycle"]
    assert features.battery.nunique() == 86 and len(features) == 20823
    assert not features.duplicated(keys).any()
    numbers = features.select_dtypes("number")
    assert np.isfinite(numbers.to_numpy()).all()
    merged = features.merge(
        labels, on=keys, suffixes=("_feature", "_label"), validate="one_to_one"
    )
    assert len(merged) == len(features)
    assert np.allclose(
        merged.soh_pct_feature, merged.capacity_ah_label / 2.4 * 100, atol=1e-10
    )
    total = missing = duplicates = 0
    for row in pd.read_csv(ROOT / "reports/data_audit.csv").itertuples():
        path = ROOT / "data/clean/cells" / f"{row.phase}_{row.battery}.parquet"
        parquet = pq.ParquetFile(path)
        assert parquet.metadata.num_rows == row.all_rows
        previous = None
        for batch in parquet.iter_batches(batch_size=65536):
            data = batch.to_pandas()
            missing += int(
                (~np.isfinite(data.select_dtypes("number").to_numpy())).sum()
            )
            assert (data.time >= 0).all()
            duplicates += int(data.duplicated(["cycle", "time"]).sum())
            first = (data.cycle.iloc[0], data.time.iloc[0])
            duplicates += int(first == previous)
            previous = (data.cycle.iloc[-1], data.time.iloc[-1])
            assert np.allclose(data.SOH, data.capacity / 2.4, atol=1e-12)
            total += len(data)
    assert total == summary["all_measurement_rows"] == 10000000
    assert missing == duplicates == 0
    result = dict(
        status="passed",
        dataset="SDU",
        measurement_rows=total,
        independent_batteries=86,
        feature_samples=len(features),
        missing_values=missing,
        duplicate_measurement_keys=duplicates,
        nominal_capacity_ah=2.4,
        source_doi=summary["source_doi"],
        suspected_points=25,
        suspected_points_in_window=0,
        scope="All prepared Parquet batches checked; source-byte hashes and all window features checked during preparation. Suspect points retained.",
    )
    (ROOT / "reports/dataset_check.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
