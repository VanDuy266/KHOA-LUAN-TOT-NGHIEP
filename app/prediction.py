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
        raise ValueError("File vượt quá 5 MB.")
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


def predict_batch(frame, artifact, limit=100):
    """Dự đoán riêng từng nhóm, giữ lỗi theo nhóm thay vì bỏ cả file."""
    if "cycle" not in frame:
        raise ValueError("CSV theo lô cần cột cycle hoặc Chu kỳ xả.")
    data = frame.copy()
    data["cycle"] = pd.to_numeric(data.cycle, errors="raise")
    if data.cycle.isna().any() or (data.cycle < 1).any() or (data.cycle % 1 != 0).any():
        raise ValueError("Số chu kỳ phải là số nguyên dương, không được thiếu.")
    if "battery" not in data:
        data["battery"] = "Không cung cấp"
    if data.battery.isna().any() or data.battery.astype(str).str.strip().eq("").any():
        raise ValueError("Mã pin không được để trống.")
    groups = data.groupby(["battery", "cycle"], sort=False)
    if groups.ngroups > limit:
        raise ValueError(f"Mỗi lần xử lý tối đa {limit} chu kỳ.")
    results = []
    for (battery, cycle), group in groups:
        row = {"battery": str(battery), "cycle": int(cycle), "measurement_count": len(group)}
        try:
            estimate, _, outside = predict(group, int(cycle), artifact)
            row.update(predicted_soh_pct=estimate, status="Thành công", outside_count=len(outside), error="")
        except (ValueError, TypeError, KeyError) as error:
            row.update(predicted_soh_pct=float("nan"), status="Không hợp lệ", outside_count=0, error=str(error))
        results.append(row)
    if not results:
        raise ValueError("CSV chưa có chu kỳ để xử lý.")
    return pd.DataFrame(results)
