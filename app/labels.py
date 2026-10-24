"""Tên hiển thị tiếng Việt; giữ tên cột gốc trong CSV để chạy lại nghiên cứu."""

MODEL_NAMES = {
    "Ridge-RF residual": "Ridge–RF hiệu chỉnh phần dư",
    "Mean baseline": "Trung bình SOH — mốc cơ sở",
    "GRU": "Mạng chuỗi thời gian — GRU",
    "LightGBM": "Tăng cường cây — LightGBM",
    "Ridge": "Hồi quy Ridge",
    "Random Forest": "Rừng ngẫu nhiên — Random Forest",
    "HistGradientBoosting": "Tăng cường cây — Histogram Boosting",
}
COLUMNS = {
    "phase": "Giai đoạn",
    "phase_code": "Giai đoạn (0/1)",
    "capacity_ah": "Dung lượng xả (Ah)",
    "importance": "Mức quan trọng",
    "feature": "Đặc trưng",
    "fit_seconds": "Thời gian học (giây)",
    "predict_seconds": "Thời gian dự đoán (giây)",
    "fold": "Vòng kiểm thử",
    "test_fold": "Vòng kiểm thử của pin",
    "rest_rows": "Dòng nghỉ",
    "conflicting_cycles_removed": "Chu kỳ xung đột đã loại",
    "status": "Trạng thái",
    "error": "Lỗi dữ liệu",
    "outside_count": "Đặc trưng ngoài miền",
    "measurement_count": "Số điểm đo",
    "created_at": "Thời điểm (UTC+7)",
    "source": "Nguồn đầu vào",
    "battery": "Mã pin",
    "cycle": "Chu kỳ xả",
    "soh_pct": "SOH (%)",
    "model": "Mô hình",
    "mae": "MAE (điểm % SOH)",
    "rmse": "RMSE (điểm % SOH)",
    "r2": "R²",
    "held_out_battery": "Pin kiểm thử",
    "n_train": "Số mẫu huấn luyện",
    "n_test": "Số mẫu kiểm thử",
    "time": "Thời gian (giây)",
    "terminal_voltage": "Điện áp (V)",
    "terminal_current": "Dòng điện (A)",
    "temperature": "Nhiệt độ (°C)",
    "ambient_temperature": "Nhiệt độ môi trường (°C)",
    "capacity": "Dung lượng xả (Ah)",
    "actual_soh": "SOH thực tế (%)",
    "predicted_soh": "SOH dự đoán (%)",
    "all_rows": "Dòng đo được chọn",
    "charge_rows": "Dòng sạc",
    "rows": "Dòng xả",
    "cycles": "Chu kỳ xả",
    "charge_cycles": "Chu kỳ sạc",
    "rows_before": "Dòng trước làm sạch",
    "invalid_rows_removed": "Dòng thiếu đã loại",
    "duplicates_removed": "Dòng trùng đã loại",
    "missing_values": "Giá trị thiếu còn lại",
    "min_soh_pct": "SOH nhỏ nhất (%)",
    "max_soh_pct": "SOH lớn nhất (%)",
    "configuration": "Cấu hình",
    "last_train_cycle": "Chu kỳ cuối huấn luyện",
    "first_test_cycle": "Chu kỳ đầu kiểm thử",
    "operation_index": "Thứ tự hoạt động",
    "operation_type": "Loại hoạt động",
    "reason": "Lý do",
    "voltage_mean": "Điện áp trung bình (V)",
    "voltage_min": "Điện áp thấp nhất (V)",
    "voltage_max": "Điện áp cao nhất (V)",
    "voltage_std": "Độ lệch chuẩn điện áp (V)",
    "voltage_slope": "Độ dốc điện áp (V/s)",
    "current_mean": "Dòng trung bình (A)",
    "current_std": "Độ lệch chuẩn dòng (A)",
    "temperature_mean": "Nhiệt độ trung bình (°C)",
    "temperature_max": "Nhiệt độ cao nhất (°C)",
    "temperature_slope": "Độ dốc nhiệt độ (°C/s)",
    "predicted_soh_pct": "SOH ước lượng (%)",
    "window_seconds": "Cửa sổ quan sát (giây)",
}
CONFIGURATIONS = {
    "Full features": "Đầy đủ đặc trưng",
    "Without cycle": "Bỏ số chu kỳ",
    "Voltage only": "Chỉ dùng nhóm điện áp",
    "Without phase": "Bỏ giai đoạn",
    "Last known SOH": "Giữ SOH cuối đã biết",
}


def vietnamese_table(frame):
    """Dịch bản sao để không làm đổi dữ liệu tính toán."""
    display = frame.copy()
    for column in ["model", "configuration"]:
        if column in display:
            names = {**MODEL_NAMES, **CONFIGURATIONS}
            display[column] = display[column].map(lambda name: names.get(name, name))
    if "phase" in display:
        display["phase"] = display.phase.replace(
            {"primary": "Sử dụng ban đầu", "second_life": "Tái sử dụng"}
        )
    if "operation_type" in display:
        display["operation_type"] = display.operation_type.replace(
            {"charge": "Sạc", "discharge": "Xả"}
        )
    if "reason" in display:
        display["reason"] = display.reason.replace(
            {
                "Missing or non-finite measured signals": "Thiếu tín hiệu đo hoặc có số vô hạn"
            }
        )
    return display.rename(columns=COLUMNS)
