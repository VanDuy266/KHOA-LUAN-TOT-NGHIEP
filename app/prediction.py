"""Kiểm tra CSV và dự đoán một chu kỳ; dùng chung với kiểm thử giao diện."""
import io
import pandas as pd
from battery_soh.features import FEATURES, extract_window

# Chấp nhận cả tên gốc và tên tiếng Việt trong các bảng tải từ ứng dụng.
INPUT_NAMES = {
    "Thời gian (giây)": "time", "Điện áp (V)": "terminal_voltage",
    "Dòng điện (A)": "terminal_current", "Nhiệt độ (°C)": "temperature",
    "Chu kỳ xả": "cycle", "Mã pin": "battery",
}


def read_csv(content):
    if len(content) > 5_000_000:
        raise ValueError("File vượt quá 5 MB. Hãy chỉ xuất một chu kỳ xả.")
    frame = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
    frame.columns = frame.columns.str.strip()
    frame = frame.rename(columns=INPUT_NAMES)
    if frame.columns.duplicated().any():
        raise ValueError("Tên cột bị trùng sau khi quy đổi về định dạng chuẩn.")
    if frame.empty:
        raise ValueError("CSV chưa có dòng dữ liệu.")
    return frame


def predict(frame, cycle, artifact):
    if "battery" in frame and frame.battery.nunique(dropna=False) != 1:
        raise ValueError("CSV phải chứa dữ liệu của đúng một pin.")
    if "cycle" in frame:
        supplied = pd.to_numeric(frame.cycle, errors="raise")
        if not supplied.eq(cycle).all():
            raise ValueError("CSV phải có đúng một chu kỳ và khớp số chu kỳ bạn nhập.")
    features = pd.DataFrame([extract_window(frame, cycle)])[FEATURES]
    outside = []
    for column in FEATURES:
        value = features[column].iloc[0]
        if value < artifact["training_min"][column] or value > artifact["training_max"][column]:
            outside.append(column)
    estimate = float(artifact["model"].predict(features)[0])
    return estimate, features, outside
