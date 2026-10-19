"""Đặc trưng SDU từ 120 giây đầu xả; nhãn dung lượng được giữ riêng."""

import numpy as np
import pandas as pd

WINDOW_SECONDS = 120.0
NOMINAL_AH = 2.4
FEATURES = [
    "phase_code",
    "cycle",
    "voltage_mean",
    "voltage_min",
    "voltage_max",
    "voltage_std",
    "voltage_slope",
    "current_mean",
    "current_std",
    "temperature_mean",
    "temperature_max",
    "temperature_slope",
]
SIGNALS = ["time", "terminal_voltage", "terminal_current", "temperature"]


def extract_window(frame, cycle, phase_code=None):
    missing = set(SIGNALS) - set(frame.columns)
    if missing:
        raise ValueError(f"Thiếu cột: {sorted(missing)}")
    if not np.isfinite(cycle) or cycle < 1 or int(cycle) != cycle:
        raise ValueError("Chu kỳ phải là số nguyên dương")
    if phase_code is None:
        if "phase_code" not in frame:
            raise ValueError("Thiếu phase_code: 0 sử dụng ban đầu, 1 tái sử dụng")
        codes = pd.to_numeric(frame.phase_code, errors="raise")
        if codes.nunique(dropna=False) != 1:
            raise ValueError("Mỗi chu kỳ phải có đúng một giai đoạn")
        phase_code = float(codes.iloc[0])
    if phase_code not in (0, 1):
        raise ValueError("phase_code phải là 0 hoặc 1")
    data = frame[SIGNALS].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(data.time).all() or (data.time < 0).any():
        raise ValueError("Thời gian phải hữu hạn và không âm")
    data = data.loc[data.time <= 120].sort_values("time")
    if not np.isfinite(data.to_numpy()).all():
        raise ValueError("Tín hiệu thiếu hoặc vô hạn")
    if data.time.duplicated().any():
        raise ValueError("Thời gian bị trùng")
    if len(data) < 5 or data.time.min() > 20 or data.time.max() < 90:
        raise ValueError(
            "Cần ít nhất 5 mẫu trong 0–120 giây, bắt đầu <=20 và kết thúc >=90 giây"
        )
    active = data[data.terminal_current < -0.1]
    if len(active) < 3 or active.time.max() - active.time.min() < 30:
        raise ValueError("Cần ít nhất 3 mẫu xả trải dài >=30 giây")
    if (
        not active.terminal_voltage.between(0, 4.5, inclusive="right").all()
        or not active.temperature.between(-40, 100).all()
    ):
        raise ValueError("Điện áp hoặc nhiệt độ ngoài miền kiểm tra")
    t = active.time.to_numpy()
    centered = t - t.mean()

    def slope(y):
        return float(np.dot(centered, y - y.mean()) / np.dot(centered, centered))

    v = active.terminal_voltage.to_numpy()
    i = active.terminal_current.to_numpy()
    temp = active.temperature.to_numpy()
    return dict(
        phase_code=int(phase_code),
        cycle=int(cycle),
        voltage_mean=v.mean(),
        voltage_min=v.min(),
        voltage_max=v.max(),
        voltage_std=v.std(),
        voltage_slope=slope(v),
        current_mean=i.mean(),
        current_std=i.std(),
        temperature_mean=temp.mean(),
        temperature_max=temp.max(),
        temperature_slope=slope(temp),
    )


def validate_target(frame, nominal_ah=NOMINAL_AH):
    if frame.empty:
        raise ValueError("Thiếu dữ liệu nhãn")
    cap = pd.to_numeric(frame.capacity).to_numpy()
    soh = pd.to_numeric(frame.SOH).to_numpy()
    if not np.isfinite(cap).all() or not np.isfinite(soh).all():
        raise ValueError("Nhãn thiếu hoặc vô hạn")
    if np.ptp(cap) > 1e-6 or np.ptp(soh) > 1e-6:
        raise ValueError("Nhãn không nhất quán")
    if not np.allclose(soh, cap / nominal_ah, rtol=0, atol=1e-6):
        raise ValueError("SOH không khớp dung lượng danh định")
    return float(100 * soh[0])
