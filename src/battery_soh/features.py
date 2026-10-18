"""Đặc trưng chỉ dùng 120 giây đầu; capacity chỉ dùng tạo nhãn."""
import numpy as np
import pandas as pd

WINDOW_SECONDS = 120.0
FEATURES = ["cycle", "voltage_mean", "voltage_min", "voltage_max", "voltage_std",
            "voltage_slope", "current_mean", "current_std", "temperature_mean",
            "temperature_max", "temperature_slope"]
SIGNALS = ["time", "terminal_voltage", "terminal_current", "temperature"]


def extract_window(frame: pd.DataFrame, cycle: int) -> dict:
    """Kiểm tra dữ liệu rồi tính thống kê tín hiệu đầu chu kỳ xả."""
    missing = set(SIGNALS) - set(frame.columns)
    if missing:
        raise ValueError(f"Thiếu cột: {sorted(missing)}")
    if not np.isfinite(cycle) or cycle < 1 or int(cycle) != cycle:
        raise ValueError("Chu kỳ phải là số nguyên dương")
    # Kiểm tra thời gian; các tín hiệu sau 120 giây không được dùng.
    time = pd.to_numeric(frame["time"], errors="raise")
    if not np.isfinite(time).all() or (time < 0).any():
        raise ValueError("Thời gian phải hữu hạn và không âm")
    window = frame.loc[time <= WINDOW_SECONDS, SIGNALS].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(window.to_numpy()).all():
        raise ValueError("Tín hiệu trong cửa sổ có giá trị thiếu hoặc vô hạn")
    if window.time.duplicated().any():
        raise ValueError("Thời gian trong chu kỳ bị trùng")
    window = window.sort_values("time")
    if len(window) < 5 or window.time.min() > 20 or window.time.max() < 90:
        raise ValueError("Cần ít nhất 5 mẫu trong 0–120 giây, bắt đầu <=20 và kết thúc >=90 giây")
    active = window.loc[window.terminal_current < -0.1]
    if len(active) < 3 or active.time.max() - active.time.min() < 30:
        raise ValueError("Cần ít nhất 3 mẫu xả với dòng < -0.1 A trải dài >=30 giây")
    # v: điện áp; i: dòng điện; t: nhiệt độ. Mỗi mảng chỉ thuộc cửa sổ xả.
    v, i, t = active.terminal_voltage, active.terminal_current, active.temperature
    if not v.between(0, 5).all() or not t.between(-40, 100).all():
        raise ValueError("Điện áp hoặc nhiệt độ ngoài miền hợp lệ cho cell lithium-ion")
    return {
        "cycle": int(cycle),
        "voltage_mean": v.mean(),
        "voltage_min": v.min(),
        "voltage_max": v.max(),
        "voltage_std": v.std(ddof=0),
        "voltage_slope": np.polyfit(active.time, v, 1)[0],
        "current_mean": i.mean(),
        "current_std": i.std(ddof=0),
        "temperature_mean": t.mean(),
        "temperature_max": t.max(),
        "temperature_slope": np.polyfit(active.time, t, 1)[0],
    }


def validate_target(frame: pd.DataFrame, nominal_ah: float = 2.0) -> float:
    """Xác nhận một chu kỳ có một nhãn nhất quán theo dung lượng danh định."""
    if frame.empty:
        raise ValueError("Không có dữ liệu chu kỳ để xác minh nhãn")
    if not np.isfinite(nominal_ah) or nominal_ah <= 0:
        raise ValueError("Dung lượng danh định phải dương")
    if not {"capacity", "SOH"}.issubset(frame.columns):
        raise ValueError("Thiếu capacity hoặc SOH để xác minh nhãn")
    capacity = pd.to_numeric(frame.capacity, errors="raise").to_numpy()
    soh = pd.to_numeric(frame.SOH, errors="raise").to_numpy()
    if not np.isfinite(capacity).all() or not np.isfinite(soh).all():
        raise ValueError("Nhãn thiếu hoặc vô hạn")
    if np.ptp(capacity) > 1e-6 or np.ptp(soh) > 1e-6:
        raise ValueError("Nhãn không nhất quán trong cùng chu kỳ")
    if not np.allclose(soh, capacity / nominal_ah, atol=1e-6, rtol=0):
        raise ValueError("SOH không khớp capacity / dung lượng danh định")
    if not 0 < soh[0] <= 1.2:
        raise ValueError("SOH không nằm trong (0, 120%]")
    return float(soh[0] * 100)
