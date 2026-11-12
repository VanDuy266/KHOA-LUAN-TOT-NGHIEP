"""Validate portable assessment data; imported results are not authenticated."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
import math
import re

from webapp.assessment import TASKS, LIMIT, profile_from, report_html
from webapp.data import MODELS

IMPORT_WARNING = "Hồ sơ được nhập từ file: chưa xác minh tính xác thực, file đo hoặc kết quả mô hình. Muốn kiểm chứng, chạy lại với dữ liệu nguồn."


def _string(value, limit=500):
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError("Hồ sơ có trường văn bản không hợp lệ hoặc quá dài.")
    return value


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Hồ sơ có giá trị số không hữu hạn hoặc sai kiểu.")
    return value


def _bounded_json(value, depth=0):
    if depth > 10:
        raise ValueError("Hồ sơ lồng nhau quá sâu.")
    if isinstance(value, dict):
        if len(value) > 128:
            raise ValueError("Hồ sơ có quá nhiều trường.")
        for key, item in value.items():
            _string(key, 120)
            _bounded_json(item, depth+1)
    elif isinstance(value, list):
        if len(value) > 500:
            raise ValueError("Một phần hồ sơ có quá nhiều dòng.")
        for item in value:
            _bounded_json(item, depth+1)
    elif isinstance(value, str):
        _string(value, 2000)
    elif value is not None and not isinstance(value, bool):
        _number(value)


def restore_record(raw):
    if not isinstance(raw, dict):
        raise ValueError("File cần một hồ sơ JSON hoặc gói sao lưu hồ sơ.")
    _bounded_json(raw)
    if len(json.dumps(raw, ensure_ascii=False).encode()) > 300000:
        raise ValueError("Một hồ sơ tối đa 300 KB.")
    task = raw.get("task")
    if task not in TASKS:
        raise ValueError("Hồ sơ không có bài toán được hỗ trợ.")
    if not re.fullmatch(r"[a-f0-9]{32}", _string(raw.get("id"), 32)):
        raise ValueError("Mã hồ sơ không hợp lệ.")
    profile = profile_from({"profile": json.dumps(raw.get("profile"))})
    if not profile["battery_id"]:
        raise ValueError("Hồ sơ cần mã pin/xe.")
    try:
        datetime.fromisoformat(raw.get("created_at", ""))
    except (ValueError, TypeError):
        raise ValueError("Thời điểm lập hồ sơ không hợp lệ.")
    model = _string(raw.get("model"), 100)
    supported = set(MODELS) if task == "sdu" else {"Random Forest", "Ridge-RF residual"} if task == "bms" else {"Tỷ lệ dung lượng đo"} if task == "capacity" else {"Tổng hợp tín hiệu đo"}
    if model not in supported:
        raise ValueError("Mô hình trong hồ sơ không khớp bài toán.")
    if not isinstance(raw.get("sample"), bool):
        raise ValueError("Trạng thái dữ liệu mẫu không hợp lệ.")
    results = raw.get("results")
    if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
        raise ValueError("Mỗi hồ sơ cần đúng một kết quả.")
    result = results[0]
    if task == "signals":
        if result.get("soh_pct") is not None:
            raise ValueError("Hồ sơ tín hiệu không được chứa kết luận SOH.")
    else:
        soh = _number(result.get("soh_pct"))
        if soh < 0 or (task in {"sdu", "bms"} and soh > 130):
            raise ValueError("SOH trong hồ sơ ngoài phạm vi hỗ trợ.")
        expected_loss = 100-soh if soh <= 100 else None
        if result.get("loss_pct") != expected_loss:
            raise ValueError("Mức chai không khớp SOH trong hồ sơ.")
        if _number(result.get("capacity_ah")) < 0:
            raise ValueError("Dung lượng trong hồ sơ không hợp lệ.")
    checks = raw.get("checks")
    if not isinstance(checks, list) or len(checks) > 20:
        raise ValueError("Bảng kiểm tra hồ sơ không hợp lệ.")
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("Bảng kiểm tra cần các dòng có tên.")
        for key in ("label", "status", "detail"):
            _string(check.get(key))
    for field in ("warnings", "next_steps"):
        if not isinstance(raw.get(field), list) or len(raw[field]) > 30:
            raise ValueError("Ghi chú hồ sơ không hợp lệ.")
        for text in raw[field]:
            _string(text, 1000)
    scope = raw.get("scope")
    if not isinstance(scope, dict) or not isinstance(scope.get("allowed"), bool):
        raise ValueError("Thông tin phạm vi trong hồ sơ không hợp lệ.")
    _string(scope.get("message"), 1000)
    for field in ("uncertainty", "label_source", "app_version"):
        _string(raw.get(field), 1000)
    for field in ("source_sha256", "model_sha256"):
        if field in raw and not re.fullmatch(r"[a-f0-9]{64}", _string(raw[field], 64)):
            raise ValueError("Mã SHA256 trong hồ sơ không hợp lệ.")
    explanation = raw.get("explanation")
    if explanation is not None:
        if not isinstance(explanation, dict) or not isinstance(explanation.get("evidence"), dict):
            raise ValueError("Giải thích hồ sơ không hợp lệ.")
        _number(explanation.get("baseline"))
        evidence = explanation["evidence"]
        for key in ("contribution_sum", "reconstructed", "reconstruction_error"):
            _number(evidence.get(key))
        if not isinstance(evidence.get("reconstruction_ok"), bool) or not isinstance(evidence.get("top_effects"), list):
            raise ValueError("Bằng chứng giải thích không hợp lệ.")
        for effect in evidence["top_effects"]:
            if not isinstance(effect, dict):
                raise ValueError("Đóng góp đặc trưng không hợp lệ.")
            _string(effect.get("feature"), 100)
            _number(effect.get("value"))
            _number(effect.get("contribution"))
    if "validation" in raw:
        if not isinstance(raw["validation"], list) or not all(isinstance(r, dict) for r in raw["validation"]):
            raise ValueError("Bảng kiểm thử không hợp lệ.")
    signals = raw.get("signals", [])
    if not isinstance(signals, list) or len(signals) > 200:
        raise ValueError("Hồ sơ tối đa 200 điểm biểu đồ.")
    keys = ("time_s", "pack_voltage", "charge_current", "max_temperature") if task == "bms" else ("time", "terminal_voltage", "terminal_current", "temperature")
    for point in signals:
        if not isinstance(point, dict):
            raise ValueError("Điểm biểu đồ không hợp lệ.")
        for key in keys:
            _number(point.get(key))
    # Never trust HTML supplied by a backup file. Rebuild from validated data.
    record = deepcopy(raw)
    record.pop("report_html", None)
    record.update(profile=profile, title=TASKS[task], limitation=LIMIT, restored=True,
                  restored_at=datetime.now(timezone.utc).isoformat())
    record["warnings"] = [IMPORT_WARNING] + [w for w in record["warnings"] if w != IMPORT_WARNING]
    return dict(record=record, report_html=report_html(record))


def restore_backup(payload):
    if not isinstance(payload, dict):
        raise ValueError("File sao lưu cần là đối tượng JSON.")
    if "records" in payload:
        if payload.get("format") != "vincent-assessments" or payload.get("version") != 1:
            raise ValueError("Định dạng hoặc phiên bản sao lưu chưa được hỗ trợ.")
        records = payload["records"]
    else:
        records = [payload]
    if not isinstance(records, list) or not 1 <= len(records) <= 100:
        raise ValueError("Gói sao lưu cần từ 1 đến 100 hồ sơ.")
    restored = [restore_record(r) for r in records]
    ids = [item["record"]["id"] for item in restored]
    if len(set(ids)) != len(ids):
        raise ValueError("Gói sao lưu chứa mã hồ sơ trùng nhau.")
    return restored


def records_trend(records, threshold=80):
    """Calendar trend of comparable client-supplied records, not RUL validation."""
    import pandas as pd
    from webapp.health import trend_forecast
    if not isinstance(records, list) or not 5 <= len(records) <= 100:
        raise ValueError("Chọn từ 5 đến 100 hồ sơ cùng pin và cùng điều kiện.")
    validated = [restore_record(r)["record"] for r in records]
    def group(record):
        p = record["profile"]
        return tuple(p.get(k) for k in ("battery_id", "origin", "chemistry", "level", "mode", "nominal_ah", "conditions")) + (
            record["task"], record["model"], record.get("model_sha256"), record.get("source_battery_id"),
            record["sample"], record["results"][0].get("phase_code"), record["results"][0].get("reference_ah"))
    if len({group(r) for r in validated}) != 1 or not validated[0]["profile"]["conditions"]:
        raise ValueError("Chỉ phân tích cùng pin, nguồn, mô hình, giai đoạn, mốc dung lượng và điều kiện đo đã ghi rõ.")
    if validated[0]["task"] == "signals":
        raise ValueError("Hồ sơ tín hiệu chưa có SOH để phân tích xu hướng.")
    dates = []
    for record in validated:
        try:
            dates.append(datetime.fromisoformat(record["profile"]["measured_at"]).date())
        except ValueError:
            raise ValueError("Mỗi hồ sơ cần ngày đo hợp lệ.")
    if len(set(dates)) != len(dates):
        raise ValueError("Mỗi ngày chỉ dùng một hồ sơ; không gộp các lần chạy lại thành nhiều mốc đo.")
    first = min(dates)
    points = [dict(position=(day-first).days, soh_pct=r["results"][0]["soh_pct"], measured_at=day.isoformat()) for day,r in zip(dates,validated)]
    points.sort(key=lambda p:p["position"])
    result = trend_forecast(pd.DataFrame(points), _number(threshold))
    crossing_date = None
    if result["crossing"] is not None:
        try:
            crossing_date = (first + timedelta(days=result["crossing"])).isoformat()
        except OverflowError:
            pass
    return dict(result=result, unit="days", first_date=first.isoformat(), crossing_date=crossing_date,
                points=points, battery_id=validated[0]["profile"]["battery_id"],
                scope="Xu hướng hồi cứu từ hồ sơ do trình duyệt cung cấp, chưa xác minh file đo; chưa kiểm chứng dự báo ngày xuống ngưỡng trên dữ liệu thực tế độc lập. Không dự báo ngày hỏng.")
