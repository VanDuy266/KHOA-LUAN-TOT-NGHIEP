"""Đọc XJTU Batch-1/2 và tạo đầu vào đầu xả; không ghi đè file MAT gốc."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.io import loadmat
from battery_soh.features import FEATURES, extract_window

NOMINAL_AH = 2.0
TRANSFER_FEATURES = [name for name in FEATURES if name != "phase_code"]


def normalized_features(data, nominal_ah):
    """Đổi dòng A thành C-rate; không dùng nhãn/dung lượng đo trong đặc trưng."""
    if nominal_ah <= 0:
        raise ValueError("Dung lượng danh định phải dương")
    result = data[TRANSFER_FEATURES].copy()
    result[["current_mean", "current_std"]] /= nominal_ah
    return result


def cycle_window(cycle):
    arrays = [np.asarray(cycle[key], dtype=float).reshape(-1) for key in
              ["voltage_V", "current_A", "temperature_C", "capacity_Ah"]]
    timestamps = np.asarray(cycle["system_time"]).reshape(-1)
    if len({len(a) for a in arrays + [timestamps]}) != 1:
        raise ValueError("Các tín hiệu không cùng chiều dài")
    voltage, current, temperature, capacity = arrays
    if not np.isfinite(np.column_stack(arrays)).all():
        raise ValueError("Tín hiệu có giá trị thiếu/vô hạn")
    discharge = current < -0.1
    if not discharge.any():
        raise ValueError("Không có đoạn xả")
    time = pd.to_datetime(timestamps, format="%Y-%m-%d,%H:%M:%S", errors="raise")
    start = time[discharge].min()
    seconds = np.asarray((time - start).total_seconds())
    take = discharge & (seconds >= 0) & (seconds <= 120)
    window = pd.DataFrame({"time": seconds[take], "terminal_voltage": voltage[take],
                           "terminal_current": current[take], "temperature": temperature[take]})
    duplicates = int(window.time.duplicated().sum())
    # Đồng hồ nguồn độ phân giải một giây: gom trung bình các phép đo cùng giây
    # chỉ ở bảng dẫn xuất. Không thay đổi nguồn và không dùng dung lượng làm đầu vào.
    window = window.groupby("time", as_index=False).mean().sort_values("time")
    return window, float(np.max(np.abs(capacity[discharge]))), duplicates


def read_cell(path, battery, batch):
    if batch not in (1, 2):
        raise ValueError("Phiên bản này chỉ xử lý Batch-1 và Batch-2")
    raw = loadmat(path, simplify_cells=True)
    expected = f"{batch + 1}C charge experiment"
    if str(raw["summary"].get("description", "")).strip() != expected:
        raise ValueError(f"Mô tả thí nghiệm không khớp Batch-{batch}; cần {expected}")
    cycles = raw["data"]
    if isinstance(cycles, dict):
        cycles = [cycles]
    capacities = np.asarray(raw["summary"]["discharge_capacity_Ah"], dtype=float).reshape(-1)
    if len(cycles) != len(capacities):
        raise ValueError("Số nhãn dung lượng khác số chu kỳ")
    rows, sequences, windows, excluded = [], [], [], []
    duplicate_seconds = raw_points = 0
    for number, (cycle, capacity) in enumerate(zip(cycles, capacities), 1):
        raw_points += len(np.asarray(cycle["voltage_V"]).reshape(-1))
        try:
            window, measured, duplicates = cycle_window(cycle)
            if not np.isfinite(capacity) or capacity <= 0:
                raise ValueError("Nhãn dung lượng không hợp lệ")
            if abs(measured - capacity) > 0.005:
                raise ValueError("Dung lượng summary lệch cực đại đoạn xả quá 0,005 Ah")
            features = extract_window(window, number, phase_code=0)
            rows.append({"battery": battery, "batch": batch, **features,
                         "capacity_ah": capacity, "soh_pct": capacity / NOMINAL_AH * 100,
                         "window_points": len(window)})
            grid = np.linspace(0, 120, 25)
            sequences.append(np.column_stack([np.interp(grid, window.time, window[c])
                             for c in ["terminal_voltage", "terminal_current", "temperature"]]))
            windows.append(window.assign(battery=battery, cycle=number))
            duplicate_seconds += duplicates
        except (ValueError, KeyError, TypeError) as error:
            excluded.append({"battery": battery, "batch": batch, "cycle": number, "reason": str(error)})
    audit = {"battery": battery, "batch": batch, "source_cycles": len(cycles),
             "raw_points": raw_points, "valid_cycles": len(rows), "excluded_cycles": len(excluded),
             "duplicate_window_seconds_aggregated": duplicate_seconds}
    return pd.DataFrame(rows), np.asarray(sequences, dtype="float32"), windows, excluded, audit
