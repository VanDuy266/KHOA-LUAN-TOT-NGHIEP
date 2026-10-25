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
            text = f"{label}: {dec(value)} {unit}; tiêu chí yêu cầu {'không quá' if comparator == 'max' else 'ít nhất'} {dec(threshold)} {unit}. Đáp ứng riêng tiêu chí này; chưa xác nhận pin an toàn."
        else:
            text = f"Đã có giá trị {dec(value)} {unit}, nhưng chưa có {'giới hạn tối đa' if comparator == 'max' else 'mốc SOH tối thiểu'} để so sánh. Nhập tiêu chí kèm nguồn ở mục Ngưỡng đối chiếu tùy chọn rồi chạy lại."
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
        "Chưa vượt các tiêu chí đã nhập" if rules else "Đã có số liệu; chưa có tiêu chí để kết luận chỉ số nào vượt giới hạn")
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
    explanation = (f"Mô hình ước tính bộ pin còn {dec(prediction)}% khả năng lưu trữ điện so với mốc danh định 145 Ah, tương đương khoảng {dec(capacity, 1)} Ah. "
        + (f"Phần dung lượng giảm ước tính là {dec(loss)}%. " if loss is not None else "Kết quả vượt mốc 100%; cần kiểm tra lại mốc danh định và dữ liệu SOC trước khi diễn giải độ chai. ")
        + "Đây là sức khỏe dung lượng (SOH), không phải phần trăm điện đang còn trong pin (SOC), và không phải quãng đường xe còn đi được.")
    missing = [
        dict(item="Giới hạn vận hành của đúng bộ pin",status="Đã nhập một phần tiêu chí; nguồn chưa được thẩm định" if rules else "Chưa cung cấp",purpose="Đối chiếu nhiệt độ sạc, chênh điện áp cell và mốc SOH; không tự dùng một ngưỡng cho mọi loại pin.",action="Bổ sung tài liệu hãng hoặc ghi rõ tiêu chí nghiên cứu trong mục Ngưỡng đối chiếu tùy chọn."),
        dict(item="Mã lỗi và trạng thái bảo vệ BMS",status="Chưa có trong đầu vào",purpose="Biết hệ thống có báo lỗi quá nhiệt, quá áp hoặc lỗi khác; một con số SOH không cho biết điều này.",action="Bổ sung bản ghi mã lỗi và trạng thái bảo vệ cùng thời điểm đo."),
        dict(item="Điện áp và mã định danh từng cell",status="Chỉ có giá trị cell nhỏ nhất/lớn nhất",purpose="Có thể tính độ chênh, nhưng chưa xác định cell nào có vấn đề.",action="Bổ sung tín hiệu riêng từng cell nếu cần khoanh vùng."),
        dict(item="Dung lượng đo độc lập để đối chiếu SOH",status="Chưa có phép đo dung lượng tham chiếu độc lập",purpose="Nhãn hiện tại suy ra từ dòng điện và SOC khi sạc; chưa xác nhận độ chai bằng phép đo độc lập.",action="Bổ sung kết quả đo dung lượng theo quy trình phù hợp và cùng mốc thời gian."),
        dict(item="Theo dõi nhiều phiên và kiểm tra trực tiếp",status="Có lịch sử tháng trước cho mẫu này" if history and len(history.get("points", [])) >= 2 else "Chưa đủ lịch sử liên kết để mô tả xu hướng",purpose="Cửa sổ đầu sạc không đại diện toàn bộ quá trình sử dụng và không thay thế kiểm tra kỹ thuật.",action="Theo dõi thêm phiên sạc; cần kiểm tra kỹ thuật để kết luận lỗi hoặc khả năng tiếp tục sử dụng."),
    ]
    report_rows = [
        {"Hạng mục":"Kết luận dung lượng", "Giá trị":headline, "Đơn vị":"", "Diễn giải":"Nhãn SOH suy ra từ vận hành; chưa đối chiếu đo dung lượng độc lập."},
        {"Hạng mục":"Đối chiếu tín hiệu", "Giá trị":comparison, "Đơn vị":"", "Diễn giải":"Chỉ so sánh với tiêu chí được nhập; hệ thống chưa xác minh nguồn ngưỡng."},
        {"Hạng mục":"Tình trạng hỏng / an toàn", "Giá trị":fault, "Đơn vị":"", "Diễn giải":"Không suy ra chẩn đoán từ một con số SOH."},
    ]
    meanings = {
        "soh_pct":"Khả năng lưu trữ điện so với mốc danh định; suy ra bằng mô hình, không phải mức điện đang còn.",
        "loss_pct":"100 trừ SOH; để trống nếu SOH vượt 100%, không ghi độ chai âm.",
        "capacity_ah":"SOH × 145/100 Ah; dung lượng tương đương ước tính, chưa đo độc lập.",
        "nominal_ah":"Mốc 145 Ah của cấu hình BAIC EU500 đang được hỗ trợ; không thay bằng mốc của pin khác.",
        "temperature_spread_max_c":"Độ chênh giữa cảm biến nóng nhất và lạnh nhất tại cùng thời điểm; chưa có vị trí cảm biến.",
        "cell_spread_max_mv":"Điện áp cell lớn nhất trừ nhỏ nhất tại cùng thời điểm, đổi sang mV; chưa xác định cell nào.",
        "observed_seconds":"Khoảng dữ liệu đầu sạc được dùng phân tích; không bao quát lúc xe chạy.",
        "measurements":"Số bản ghi trong cửa sổ, không phải số cell pin.",
    }
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
        report_rows.append({"Hạng mục":label,"Giá trị":metrics[key],"Đơn vị":unit,"Diễn giải":meanings.get(key, "Giá trị quan sát trong cửa sổ đầu sạc; cần đối chiếu giới hạn của đúng cấu hình pin, không tự kết luận tốt/xấu.")})
    for item in indicators:
        report_rows.append({"Hạng mục":"Đối chiếu · "+item["label"],"Giá trị":item["value"],"Đơn vị":item["unit"],"Diễn giải":item["explanation"]})
    if limits["source"]:
        report_rows.append({"Hạng mục":"Nguồn/ghi chú tiêu chí do người dùng nhập","Giá trị":limits["source"],"Đơn vị":"","Diễn giải":"Nguồn này chưa được hệ thống thẩm định."})
    report_rows.append({"Hạng mục":"Hiểu kết quả dung lượng","Giá trị":explanation,"Đơn vị":"","Diễn giải":"SOH khác SOC; chưa suy ra an toàn hoặc quãng đường."})
    for item in missing:
        report_rows.append({"Hạng mục":"Dữ liệu cần bổ sung · "+item["item"],"Giá trị":item["status"],"Đơn vị":"","Diễn giải":item["purpose"]+" "+item["action"]})
    for item in alerts:
        report_rows.append({"Hạng mục":"Điểm cần kiểm tra","Giá trị":item["text"],"Đơn vị":"","Diễn giải":"Không phải kết luận pin hỏng."})
    return dict(headline=headline,level="review" if alerts else "info",comparison=comparison,
        fault_status=fault,explanation=explanation,missing=missing,metrics=metrics,indicators=indicators,alerts=alerts,recommendations=recommendations,
        limits=limits,source=source,history=history or dict(points=[],message="Chưa có lịch sử liên kết với dữ liệu này."),report_rows=report_rows,
        scope="BAIC EU500 · bộ pin 145 Ah · nhãn dung lượng vận hành suy ra từ dòng điện/SOC")
