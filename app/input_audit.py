"""Kiểm tra cấu trúc và từng chu kỳ mà không gọi mô hình dự đoán."""

import numpy as np
import pandas as pd
from battery_soh.features import SIGNALS, extract_window
from prediction import MAX_BATCH_CYCLES


def audit_frame(frame):
    required = [*SIGNALS, "cycle", "phase_code"]
    schema = []
    for name in required:
        present = name in frame
        numeric = pd.to_numeric(frame[name], errors="coerce") if present else pd.Series(dtype=float)
        schema.append({
            "Cột": name, "Có trong file": present,
            "Giá trị thiếu": int(frame[name].isna().sum()) if present else len(frame),
            "Không phải số hoặc vô hạn": int(((~np.isfinite(numeric)) & frame[name].notna()).sum()) if present else 0,
        })
    missing = [name for name in required if name not in frame]
    columns = ["battery", "phase_code", "cycle", "measurement_count", "status", "error"]
    if missing:
        return pd.DataFrame(schema), pd.DataFrame(columns=columns), "Thiếu cột: " + ", ".join(missing)
    data = frame.copy()
    if "battery" not in data:
        data["battery"] = "Không cung cấp"
    for name in ["cycle", "phase_code"]:
        data[name] = pd.to_numeric(data[name], errors="coerce")
    bad = (~np.isfinite(data.cycle) | data.cycle.lt(1) | data.cycle.mod(1).ne(0)
           | ~data.phase_code.isin([0, 1]) | data.battery.isna()
           | data.battery.astype(str).str.strip().eq(""))
    issue = f"{int(bad.sum())} dòng có mã pin, chu kỳ hoặc giai đoạn không hợp lệ; cần sửa trước khi dự đoán." if bad.any() else ""
    groups = data[~bad].groupby(["battery", "phase_code", "cycle"], sort=False)
    if groups.ngroups > MAX_BATCH_CYCLES:
        return pd.DataFrame(schema), pd.DataFrame(columns=columns), f"Vượt giới hạn {MAX_BATCH_CYCLES} chu kỳ/file."
    results = []
    for (battery, phase, cycle), group in groups:
        row = dict(battery=str(battery), phase_code=int(phase), cycle=int(cycle), measurement_count=len(group))
        try:
            extract_window(group, int(cycle))
            row.update(status="Hợp lệ", error="")
        except (ValueError, TypeError, KeyError) as error:
            row.update(status="Không hợp lệ", error=str(error))
        results.append(row)
    if frame.empty:
        issue = "File chưa có dòng dữ liệu."
    return pd.DataFrame(schema), pd.DataFrame(results, columns=columns), issue
