"""Kiểm tra CSV và dự đoán một chu kỳ; dùng chung với kiểm thử giao diện."""

import io
import gzip
import numpy as np
import pandas as pd
from battery_soh.features import FEATURES, extract_window

# Chấp nhận cả tên gốc và tên tiếng Việt trong các bảng tải từ ứng dụng.
INPUT_NAMES = {
    "Thời gian (giây)": "time",
    "Điện áp (V)": "terminal_voltage",
    "Dòng điện (A)": "terminal_current",
    "Nhiệt độ (°C)": "temperature",
    "Chu kỳ xả": "cycle",
    "Mã pin": "battery",
    "Giai đoạn (0/1)": "phase_code",
}


MAX_UPLOAD_BYTES = 512 * 1024 * 1024
MAX_BATCH_CYCLES = 2000
RAW_NAMES = {
    "Test_Time(s)": "time",
    "Cycle_Index": "cycle",
    "Battery_ID": "battery",
    "Voltage(V)": "terminal_voltage",
    "Current(A)": "terminal_current",
    "Aux_Temperature_1(C)": "temperature",
}


def csv_chunks(content):
    """Đọc từng khối; nhận gzip theo nội dung dù Windows ẩn phần mở rộng."""
    stream = io.BytesIO(content)
    source = gzip.GzipFile(fileobj=stream) if content[:2] == b"\x1f\x8b" else stream
    return pd.read_csv(source, encoding="utf-8-sig", chunksize=50000)


def normalize_columns(frame):
    frame.columns = frame.columns.str.strip()
    frame = frame.rename(columns={**INPUT_NAMES, **RAW_NAMES})
    if frame.columns.duplicated().any():
        raise ValueError("Tên cột bị trùng sau khi quy đổi về định dạng chuẩn.")
    return frame


def read_csv(content, phase_code=None):
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("File vượt quá 512 MiB.")
    if not content:
        raise ValueError("CSV chưa có dòng dữ liệu.")
    reader = csv_chunks(content)
    try:
        first = next(reader)
    except StopIteration:
        raise ValueError("CSV chưa có dòng dữ liệu.")
    raw = "Test_Time(s)" in first.columns.str.strip()
    if not raw:
        chunks = [normalize_columns(first)]
        chunks.extend(normalize_columns(chunk) for chunk in reader)
        frame = pd.concat(chunks, ignore_index=True)
        if frame.empty:
            raise ValueError("CSV chưa có dòng dữ liệu.")
        if "phase_code" not in frame and phase_code is not None:
            frame["phase_code"] = phase_code
        return frame
    # Thời gian của nguồn là thời gian toàn thí nghiệm. Tìm đầu xả theo
    # pin/chu kỳ trước khi lấy cửa sổ, kể cả khi thứ tự nguồn đi lùi nhẹ.
    if phase_code not in (0, 1):
        raise ValueError("CSV nguồn SDU cần chọn giai đoạn sử dụng.")
    starts = {}

    def active_rows(chunk):
        chunk = normalize_columns(chunk)
        required = {
            "battery",
            "cycle",
            "time",
            "terminal_voltage",
            "terminal_current",
            "temperature",
        }
        if required - set(chunk):
            raise ValueError(
                "CSV nguồn thiếu cột: " + ", ".join(sorted(required - set(chunk)))
            )
        chunk = chunk[list(required)].copy()
        for column in required:
            chunk[column] = pd.to_numeric(chunk[column], errors="raise")
        if not np.isfinite(chunk[["battery", "cycle", "time"]].to_numpy()).all():
            raise ValueError("Mã pin, chu kỳ và thời gian phải hữu hạn.")
        chunk = chunk[chunk.terminal_current < -0.1]
        if ((chunk.cycle < 1) | (chunk.cycle % 1 != 0)).any():
            raise ValueError("Số chu kỳ phải là số nguyên dương.")
        return chunk

    # Đọc lại từ đầu thay vì giữ cả file đã giải nén trong RAM.
    for chunk in csv_chunks(content):
        active = active_rows(chunk)
        for key, value in active.groupby(["battery", "cycle"]).time.min().items():
            starts[key] = min(starts.get(key, float("inf")), value)
    if not starts:
        raise ValueError("CSV nguồn không có đoạn xả dòng âm.")
    if len(starts) > MAX_BATCH_CYCLES:
        raise ValueError(f"Mỗi file tối đa {MAX_BATCH_CYCLES} chu kỳ xả.")
    windows = []
    for chunk in csv_chunks(content):
        active = active_rows(chunk)
        offsets = np.array(
            [starts[(b, c)] for b, c in zip(active.battery, active.cycle)]
        )
        active["time"] = active.time.to_numpy() - offsets
        active = active[active.time <= 120].copy()
        if not active.empty:
            active["battery"] = active.battery.map(lambda x: f"SDU_{int(x):02d}")
            active["phase_code"] = int(phase_code)
            windows.append(active)
    frame = pd.concat(windows, ignore_index=True).sort_values(
        ["battery", "cycle", "time"]
    )
    frame.attrs["source_format"] = "sdu_raw"
    return frame


def predict(frame, cycle, artifact):
    if "battery" in frame and frame.battery.nunique(dropna=False) != 1:
        raise ValueError("CSV phải chứa dữ liệu của đúng một pin.")
    if "cycle" in frame:
        supplied = pd.to_numeric(frame.cycle, errors="raise")
        if not supplied.eq(cycle).all():
            raise ValueError("CSV phải có đúng một chu kỳ và khớp số chu kỳ bạn nhập.")
    if artifact.get("dataset") != "SDU":
        raise ValueError("Mô hình không khớp SDU")
    features = pd.DataFrame([extract_window(frame, cycle)])[FEATURES]
    outside = []
    for column in FEATURES:
        value = features[column].iloc[0]
        if value < artifact["training_min"][column] - 1e-10 * max(
            1, abs(artifact["training_min"][column])
        ) or value > artifact["training_max"][column] + 1e-10 * max(
            1, abs(artifact["training_max"][column])
        ):
            outside.append(column)
    estimate = float(artifact["model"].predict(features)[0])
    return estimate, features, outside


def predict_batch(frame, artifact, limit=MAX_BATCH_CYCLES):
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
    if "phase_code" not in data:
        raise ValueError("CSV cần phase_code (0 hoặc 1)")
    data["phase_code"] = pd.to_numeric(data.phase_code, errors="raise")
    if not data.phase_code.isin([0, 1]).all():
        raise ValueError("phase_code phải là 0 hoặc 1")
    groups = data.groupby(["battery", "phase_code", "cycle"], sort=False)
    if groups.ngroups > limit:
        raise ValueError(f"Mỗi lần xử lý tối đa {limit} chu kỳ.")
    results = []
    for (battery, phase_code, cycle), group in groups:
        row = {
            "battery": str(battery),
            "phase_code": int(phase_code),
            "cycle": int(cycle),
            "measurement_count": len(group),
        }
        try:
            estimate, _, outside = predict(group, int(cycle), artifact)
            row.update(
                predicted_soh_pct=estimate,
                status="Thành công",
                outside_count=len(outside),
                error="",
            )
        except (ValueError, TypeError, KeyError) as error:
            row.update(
                predicted_soh_pct=float("nan"),
                status="Không hợp lệ",
                outside_count=0,
                error=str(error),
            )
        results.append(row)
    if not results:
        raise ValueError("CSV chưa có chu kỳ để xử lý.")
    return pd.DataFrame(results)
