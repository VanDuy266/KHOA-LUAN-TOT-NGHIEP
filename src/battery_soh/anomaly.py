"""Đặc trưng giám sát SOH chỉ dùng hiện tại và lịch sử đã quan sát."""

import numpy as np
import pandas as pd

WINDOW = 8
MIN_HISTORY = 5
COLUMNS = ["rate_per100", "innovation_pp", "robust_z", "prior_rate_per100"]


def trend_features(frame):
    required = {"battery", "phase", "cycle", "soh_pct"}
    if required - set(frame):
        raise ValueError("Thiếu cột: " + ", ".join(sorted(required - set(frame))))
    data = frame[list(required)].copy()
    if data[["battery", "phase"]].isna().any().any():
        raise ValueError("Thiếu mã pin hoặc giai đoạn")
    for name in ["cycle", "soh_pct"]:
        data[name] = pd.to_numeric(data[name], errors="raise")
    if not np.isfinite(data[["cycle", "soh_pct"]].to_numpy()).all():
        raise ValueError("Chu kỳ và SOH phải hữu hạn")
    if (data.cycle <= 0).any() or (data.cycle % 1 != 0).any():
        raise ValueError("Chu kỳ phải là số nguyên dương")
    if data.duplicated(["battery", "phase", "cycle"]).any():
        raise ValueError("Trùng khóa pin, giai đoạn và chu kỳ")
    results = []
    for _, part in data.groupby(["battery", "phase"], sort=True):
        part = part.sort_values("cycle").copy()
        gap = part.cycle.diff()
        delta = part.soh_pct.diff()
        rate = delta / gap
        history = rate.shift(1).rolling(WINDOW, min_periods=MIN_HISTORY)
        median = history.median()
        # MAD lấy riêng trên cửa sổ quá khứ, không dùng thống kê toàn đường cong.
        mad = history.apply(lambda x: np.nanmedian(np.abs(x - np.nanmedian(x))), raw=True)
        expected = part.soh_pct.shift(1) + median * gap
        part["expected_soh"] = expected
        part["innovation_pp"] = part.soh_pct - expected
        part["rate_per100"] = rate * 100
        part["prior_rate_per100"] = median * 100
        part["robust_z"] = (rate - median) / np.maximum(1.4826 * mad, 0.01)
        part["eligible"] = part[COLUMNS].notna().all(axis=1)
        part["rule_flag"] = (
            part.eligible
            & (part.robust_z.abs() > 4.5)
            & (part.innovation_pp.abs() >= 1.0)
        )
        results.append(part)
    if not results:
        raise ValueError("Chưa có mẫu SOH")
    return pd.concat(results, ignore_index=True)


def explain(row):
    if not row.eligible:
        return "Chưa đủ lịch sử"
    reasons = []
    if row.rule_flag:
        reasons.append(
            "SOH giảm lệch xu hướng"
            if row.innovation_pp < 0
            else "SOH tăng lệch xu hướng"
        )
    if row.iforest_flag:
        reasons.append("Isolation Forest: diễn biến ít gặp")
    return "; ".join(reasons) if reasons else "Chưa có cờ theo tiêu chí"
