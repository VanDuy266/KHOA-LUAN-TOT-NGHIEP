"""Explain BMS estimates and measured signals without inventing fault diagnoses."""
import math

LIMIT_FIELDS = {
    "limit_temperature_max": ("temperature_max_c", -30, 85),
    "limit_cell_spread_mv": ("cell_spread_max_mv", 0, 2500),
    "limit_soh_min": ("soh_min_pct", 0, 100),
}


def read_limits(values):
    limits = {}
    for name, (key, low, high) in LIMIT_FIELDS.items():
        raw = str(values.get(name, "")).strip()
        if not raw:
            continue
        try:
            number = float(raw)
        except ValueError:
            raise ValueError("Ngưỡng đối chiếu phải là số.")
        if not math.isfinite(number) or not low <= number <= high:
            raise ValueError(f"Ngưỡng {name} phải nằm trong {low}–{high}.")
        limits[key] = number
    source = str(values.get("limit_source", "")).strip()
    if len(source) > 300:
        raise ValueError("Nguồn/ghi chú ngưỡng tối đa 300 ký tự.")
    if limits and not source:
        raise ValueError("Ghi nguồn hoặc ý nghĩa của các ngưỡng đối chiếu đã nhập.")
    return dict(values=limits, source=source)


def dec(value, digits=2):
    return f"{value:.{digits}f}".replace(".", ",")


def assess(window, prediction, outside, limits, source, history=None):
    if not math.isfinite(prediction) or prediction < 0:
        raise ValueError("Mô hình trả SOH không hợp lệ; không thể diễn giải độ suy giảm.")
    loss = 100 - prediction if prediction <= 100 else None
    capacity = prediction / 100 * 145
    metrics = {
        "soh_pct": prediction, "loss_pct": loss, "capacity_ah": capacity, "nominal_ah": 145,
        "temperature_min_c": float(window.min_temperature.min()),
        "temperature_max_c": float(window.max_temperature.max()),
        "temperature_spread_max_c": float((window.max_temperature-window.min_temperature).max()),
        "cell_voltage_min_v": float(window.min_cell_voltage.min()),
        "cell_voltage_max_v": float(window.max_cell_voltage.max()),
        "cell_spread_max_mv": float(((window.max_cell_voltage-window.min_cell_voltage)*1000).max()),
        "pack_voltage_min_v": float(window.pack_voltage.min()),
        "pack_voltage_max_v": float(window.pack_voltage.max()),
        "charge_current_min_a": float((-window.charge_current).min()),
        "charge_current_max_a": float((-window.charge_current).max()),
        "soc_start_pct": float(window.soc.iloc[0]), "soc_end_pct": float(window.soc.iloc[-1]),
        "soc_change_pp": float(window.soc.iloc[-1]-window.soc.iloc[0]),
        "observed_seconds": float(window.time_s.max()), "measurements": len(window),
    }
    rules = limits["values"]
    indicators = []
    alerts = []
    for key, label, value, limit_key, comparator, unit in [
        ("temperature", "Nhiệt độ cao nhất", metrics["temperature_max_c"], "temperature_max_c", "max", "°C"),
        ("cell_spread", "Chênh điện áp cell lớn nhất", metrics["cell_spread_max_mv"], "cell_spread_max_mv", "max", "mV"),
        ("capacity", "SOH ước tính", prediction, "soh_min_pct", "min", "%"),
    ]:
        threshold = rules.get(limit_key)
        exceeds = None if threshold is None else (False if math.isclose(value, threshold, rel_tol=1e-9, abs_tol=1e-9) else (value > threshold if comparator == "max" else value < threshold))
        status = "unset" if exceeds is None else "exceeded" if exceeds else "within"
        if exceeds:
            amount = value-threshold if comparator == "max" else threshold-value
            relation = "cao hơn" if comparator == "max" else "thấp hơn"
            text = f"{label} {dec(value)} {unit}, {relation} ngưỡng {dec(threshold)} {unit} đã nhập {dec(amount)} {unit}."
            alerts.append(dict(code=key, text=text))
        elif threshold is not None:
            text = "Không vượt tiêu chí đã nhập; chưa phải xác nhận an toàn hay độ chính xác SOH vật lý."
        else:
            text = "Chưa nhập ngưỡng đối chiếu. Giá trị hiển thị là số đo hoặc ước tính, chưa phân loại tốt/xấu."
        indicators.append(dict(code=key, label=label, value=value, unit=unit, threshold=threshold, status=status, explanation=text))
    if prediction > 100:
        alerts.append(dict(code="above_nominal", text="SOH ước tính vượt 100%. Cần đối chiếu mốc danh định và nhãn/SOC; không ghi độ chai âm."))
    if outside:
        alerts.append(dict(code="outside", text="Đặc trưng vượt khoảng min/max của tập học: "+", ".join(outside)+". Cần thận trọng khi diễn giải."))
    if loss is None:
        headline = "Ước tính vượt mốc dung lượng danh định — cần đối chiếu"
    elif loss < .005:
        headline = "Dung lượng ước tính gần mốc danh định"
    else:
        headline = f"Ước tính suy giảm {dec(loss)}% dung lượng so với danh định"
    comparison = "Cần kiểm tra theo các tiêu chí đã nhập" if any(x["status"] == "exceeded" for x in indicators) else (
        "Chưa vượt các tiêu chí đã nhập" if rules else "Chưa có ngưỡng để phân loại tín hiệu")
    recommendations = []
    if any(x["status"] == "exceeded" for x in indicators):
        recommendations.append("Đối chiếu các chỉ số bị gắn cờ với tài liệu của đúng cấu hình pin và kiểm tra lại phép đo.")
    if not rules:
        recommendations.append("Bổ sung giới hạn từ tài liệu cấu hình pin nếu cần đối chiếu nhiệt độ, chênh điện áp hoặc mốc dung lượng.")
    if outside or prediction > 100:
        recommendations.append("Kiểm tra lại dung lượng danh định, quy ước dòng điện/SOC và mức phù hợp của dữ liệu với tập học.")
    recommendations += ["Theo dõi nhiều phiên sạc để đối chiếu xu hướng; một cửa sổ ngắn không xác nhận được tình trạng vận hành lâu dài.",
        "Để kết luận lỗi cụ thể hoặc pin hỏng, cần mã lỗi BMS, tín hiệu từng cell và/hoặc phép đo dung lượng, kiểm định phù hợp."]
    fault = "Chưa đủ dữ liệu xác định pin hỏng hoặc xác nhận tiếp tục sử dụng an toàn"
    report_rows = [
        {"Hạng mục":"Kết luận dung lượng", "Giá trị":headline, "Đơn vị":"", "Diễn giải":"Nhãn SOH suy ra từ vận hành; chưa đối chiếu đo dung lượng độc lập."},
        {"Hạng mục":"Đối chiếu tín hiệu", "Giá trị":comparison, "Đơn vị":"", "Diễn giải":"Chỉ so sánh với tiêu chí được nhập; hệ thống chưa xác minh nguồn ngưỡng."},
        {"Hạng mục":"Tình trạng hỏng / an toàn", "Giá trị":fault, "Đơn vị":"", "Diễn giải":"Không suy ra chẩn đoán từ một con số SOH."},
    ]
    for label, key, unit in [
        ("SOH ước tính","soh_pct","%"),("Suy giảm so với danh định","loss_pct","%"),
        ("Dung lượng tương đương ước tính","capacity_ah","Ah"),("Dung lượng danh định","nominal_ah","Ah"),
        ("Nhiệt độ nhỏ nhất","temperature_min_c","°C"),("Nhiệt độ lớn nhất","temperature_max_c","°C"),
        ("Chênh nhiệt độ cảm biến lớn nhất cùng thời điểm","temperature_spread_max_c","°C"),
        ("Điện áp cell nhỏ nhất","cell_voltage_min_v","V"),("Điện áp cell lớn nhất","cell_voltage_max_v","V"),
        ("Chênh điện áp cell lớn nhất cùng thời điểm","cell_spread_max_mv","mV"),
        ("Điện áp bộ pin thấp nhất","pack_voltage_min_v","V"),("Điện áp bộ pin cao nhất","pack_voltage_max_v","V"),
        ("Biên độ dòng sạc nhỏ nhất","charge_current_min_a","A"),("Biên độ dòng sạc lớn nhất","charge_current_max_a","A"),
        ("SOC đầu cửa sổ","soc_start_pct","%"),("SOC cuối cửa sổ","soc_end_pct","%"),
        ("Khoảng quan sát từ đầu sạc","observed_seconds","s"),("Số điểm đo","measurements","điểm"),
    ]:
        report_rows.append({"Hạng mục":label,"Giá trị":metrics[key],"Đơn vị":unit,"Diễn giải":"Trong cửa sổ đo đầu sạc; dung lượng/SOH là ước tính theo mô hình."})
    for item in indicators:
        report_rows.append({"Hạng mục":"Đối chiếu · "+item["label"],"Giá trị":item["value"],"Đơn vị":item["unit"],"Diễn giải":item["explanation"]})
    if limits["source"]:
        report_rows.append({"Hạng mục":"Nguồn/ghi chú tiêu chí do người dùng nhập","Giá trị":limits["source"],"Đơn vị":"","Diễn giải":"Nguồn này chưa được hệ thống thẩm định."})
    for item in alerts:
        report_rows.append({"Hạng mục":"Điểm cần kiểm tra","Giá trị":item["text"],"Đơn vị":"","Diễn giải":"Không phải kết luận pin hỏng."})
    return dict(headline=headline,level="review" if alerts else "info",comparison=comparison,
        fault_status=fault,metrics=metrics,indicators=indicators,alerts=alerts,recommendations=recommendations,
        limits=limits,source=source,history=history or dict(points=[],message="Chưa có lịch sử liên kết với dữ liệu này."),report_rows=report_rows,
        scope="BAIC EU500 · bộ pin 145 Ah · nhãn dung lượng vận hành suy ra từ dòng điện/SOC")
