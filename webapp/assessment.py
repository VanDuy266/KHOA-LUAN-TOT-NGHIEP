"""Assessment records with explicit scope, quality gates and portable reports.

No uploads or assessment records are persisted on the server.
"""
from datetime import datetime, timezone
from html import escape
import hashlib
import json
import math
from uuid import uuid4

import numpy as np
import pandas as pd

from webapp.data import ROOT, MODELS, table, evaluation_metrics
from webapp.column_mapping import normalize_frame, validate_filter_column, BMS_COLUMNS
from webapp.upload_table import read_upload, upload_sha256, carry_context
from webapp.external import analyze
from input_audit import audit_frame

TASKS = {
    "sdu": "Ước lượng SOH · cell SDU NMC 2,4 Ah",
    "bms": "Ước lượng SOH vận hành · BAIC EU500 145 Ah",
    "signals": "Phân tích tín hiệu · pin khác hoặc chưa rõ cấu hình",
    "capacity": "Tính SOH từ dung lượng xả đo đầy đủ",
}
LIMIT = "Không xác nhận hư hỏng, độ an toàn hoặc quyết định thay pin từ kết quả này."


def profile_from(form):
    try:
        profile = json.loads(form.get("profile", "{}"))
    except (ValueError, TypeError):
        raise ValueError("Hồ sơ pin không hợp lệ.")
    if not isinstance(profile, dict):
        raise ValueError("Hồ sơ pin cần là một đối tượng.")
    result = {}
    for key in ("battery_id", "measured_at", "conditions", "chemistry", "level", "mode", "origin"):
        value = profile.get(key, "")
        if not isinstance(value, str) or len(value) > 300:
            raise ValueError("Thông tin hồ sơ phải là văn bản tối đa 300 ký tự.")
        result[key] = value.strip()
    nominal = profile.get("nominal_ah")
    try:
        nominal = None if nominal in (None, "") else float(nominal)
    except (ValueError, TypeError):
        raise ValueError("Dung lượng định mức cần là số Ah.")
    if nominal is not None and (not math.isfinite(nominal) or nominal <= 0):
        raise ValueError("Dung lượng định mức cần hữu hạn và lớn hơn 0.")
    result["nominal_ah"] = nominal
    if result["measured_at"]:
        try:
            datetime.fromisoformat(result["measured_at"])
        except ValueError:
            raise ValueError("Ngày đo cần theo định dạng ISO, ví dụ 2026-11-12.")
    return result


def scope_check(task, profile, sample, confirmed):
    if task not in TASKS:
        raise ValueError("Bài toán không được hỗ trợ.")
    if sample:
        return True, "Dữ liệu mẫu minh họa; đã tham gia huấn luyện mô hình bàn giao."
    if not profile["battery_id"] or not profile["measured_at"]:
        return False, "Cần mã pin/xe và ngày đo để lập hồ sơ đánh giá."
    if task in {"sdu", "bms"} and not confirmed:
        return False, "Cần xác nhận nguồn, cấu hình và cửa sổ đầu sạc/xả đúng phạm vi mô hình."
    if task == "sdu" and not (
        profile["origin"] == "SDU" and profile["chemistry"] == "NMC"
        and profile["level"] == "cell" and profile["mode"] == "discharge"
        and profile["nominal_ah"] == 2.4
    ):
        return False, "Mô hình SDU chỉ dùng cho dữ liệu đầu xả cell SDU NMC 2,4 Ah. Chọn Phân tích tín hiệu cho pin khác."
    if task == "bms" and not (
        profile["origin"] == "BAIC EU500" and profile["chemistry"] == "NMC"
        and profile["level"] == "pack" and profile["mode"] == "charge"
        and profile["nominal_ah"] == 145
    ):
        return False, "Mô hình BAIC chỉ dùng cho cửa sổ đầu sạc bộ pin BAIC EU500 NMC 145 Ah."
    return True, "Hồ sơ phù hợp phạm vi đã khai báo; chưa chứng minh khả năng tổng quát hóa sang nguồn mới."


def prepare(form, files, bms_validator):
    task = form.get("task", "")
    profile = profile_from(form)
    sample = form.get("sample") == "1"
    if sample:
        profile.update(battery_id="Mẫu BAIC 01" if task == "bms" else "SDU_01",
                       origin="BAIC EU500" if task == "bms" else "SDU",
                       chemistry="NMC", level="pack" if task == "bms" else "cell",
                       mode="charge" if task == "bms" else "discharge",
                       nominal_ah=145 if task == "bms" else 2.4)
    allowed, message = scope_check(task, profile, sample, form.get("confirmed") == "1")
    base = dict(task=task, profile=profile, sample=sample, ready=False,
                scope=dict(allowed=allowed, message=message), checks=[], warnings=[])
    if not allowed:
        return base, None
    if task == "capacity":
        if sample:
            raise ValueError("Phép đo dung lượng cần giá trị đo thực, không có chế độ dữ liệu mẫu.")
        vals = {}
        for key in ("reference_ah", "measured_ah"):
            try:
                vals[key] = float(form.get(key, ""))
            except (TypeError, ValueError):
                raise ValueError("Cần hai dung lượng đo hợp lệ, cùng đơn vị Ah.")
            if not math.isfinite(vals[key]) or vals[key] <= 0:
                raise ValueError("Dung lượng phải hữu hạn và lớn hơn 0.")
        if form.get("comparable") != "1":
            raise ValueError("Cần xác nhận phép đo cùng pin và cùng điều kiện đối chiếu.")
        if not math.isfinite(100 * vals["measured_ah"] / vals["reference_ah"]):
            raise ValueError("Tỷ lệ dung lượng không hữu hạn.")
        base.update(ready=True, capacity=vals, source_sha256=hashlib.sha256(json.dumps(vals,sort_keys=True).encode()).hexdigest())
        base["checks"] = [dict(label="Phép đo dung lượng", status="Đạt", detail="Đã xác nhận cùng điều kiện; độ chính xác phụ thuộc thiết bị và phép đo.")]
        return base, None
    model = form.get("model", "Random Forest")
    if ((task == "sdu" and model not in MODELS)
            or (task == "bms" and model not in {"Random Forest", "Ridge-RF residual"})):
        raise ValueError("Mô hình chưa hỗ trợ cho bài toán này.")
    if sample:
        path = "data/bms/processed/01_example.csv.gz" if task == "bms" else "data/clean/sample_measurements.csv"
        frame = table(path).copy()
        if task != "bms":
            phase = int(form.get("phase_code", "0"))
            if phase not in (0, 1):
                raise ValueError("Giai đoạn cần là 0 hoặc 1.")
            frame = frame[(frame.battery == "SDU_01") & (frame.phase_code == phase) & (frame.cycle == 1) & (frame.time <= 120)].copy()
        base.update(source_name="Dữ liệu mẫu · " + path.split("/")[-1], source_sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest())
    else:
        upload = files.get("file")
        if upload is None or not upload.filename:
            raise ValueError("Chọn file dữ liệu trước khi kiểm tra.")
        header = read_upload(upload, preview=True)
        if task == "bms":
            missing = [name for name in BMS_COLUMNS if name not in header]
            if missing:
                raise ValueError("Tệp không đúng cấu trúc BMS BAIC EU500. Thiếu cột: " + ", ".join(missing) + ". Chọn phân tích số đo cho tệp khác; không đổi tên cột để ép chạy mô hình BAIC.")
        filters = {}
        chosen = {}
        for key in ("battery", "cycle", "phase", "step"):
            col = form.get("filter_" + key + "_column", "")
            val = form.get("filter_" + key + "_value", "")
            chosen[key] = col
            if col:
                validate_filter_column(key, col, header.columns, task)
                if col in filters:
                    raise ValueError("Các bộ lọc phải dùng cột riêng.")
                filters[col] = val
        source = read_upload(upload, filters=filters)
        base["filters"] = dict(filters)
        base.update(source_name=upload.filename.replace("\\", "/").split("/")[-1][:120], source_sha256=upload_sha256(upload))
        if task == "bms":
            for group in ("vehicle", "session"):
                if group in source and source[group].nunique(dropna=False) != 1:
                    raise ValueError("Một hồ sơ BMS cần một xe và một phiên sạc; hãy tách hoặc lọc file.")
            if "vehicle" in source:
                base["source_battery_id"] = str(source.vehicle.iloc[0])
            frame = source
        else:
            try:
                mapping = json.loads(form.get("mapping", "{}"))
                units = json.loads(form.get("units", "{}"))
            except (ValueError, TypeError):
                raise ValueError("Ánh xạ cột hoặc đơn vị không hợp lệ.")
            if not isinstance(mapping, dict) or not isinstance(units, dict):
                raise ValueError("Ánh xạ và đơn vị cần là đối tượng có tên.")
            for column in mapping.values():
                if isinstance(column, str) and column in source:
                    numeric = pd.to_numeric(source[column], errors="coerce")
                    bad_rows = np.flatnonzero(~np.isfinite(numeric.to_numpy(dtype=float)))
                    if len(bad_rows):
                        positions = ", ".join(str(int(i)+1) for i in bad_rows[:10])
                        raise ValueError(f"Cột {column}: {len(bad_rows)} giá trị thiếu/không phải số/vô hạn. Dòng dữ liệu trong đoạn đã lọc: {positions}.")
            raw_sdu = task == "sdu" and str(mapping.get("time", "")).strip().casefold() == "test_time(s)"
            if raw_sdu and form.get("positive_discharge") == "1":
                raise ValueError("Tệp SDU gốc quy ước dòng xả âm. Bỏ tùy chọn đổi dấu dòng điện để không lấy nhầm bước sạc.")
            if raw_sdu:
                source = source.sort_values(mapping["time"], key=lambda values: pd.to_numeric(values, errors="raise"), kind="stable")
            frame = normalize_frame(source, mapping, units, form.get("positive_discharge") == "1")
            frame = carry_context(frame, source, chosen)
            if raw_sdu:
                frame = frame[frame.terminal_current < -.1].copy()
                if frame.empty:
                    raise ValueError("Nhóm đã chọn không có đoạn xả dòng âm. Bỏ bộ lọc bước đo hoặc chọn bước xả; không dùng bước sạc để dự đoán SDU.")
                discharge_start = float(frame.time.min())
                frame["time"] -= discharge_start
                frame = frame[frame.time <= 120].copy()
                base["window"] = dict(method="first_discharge", offset_from_selected_start_seconds=discharge_start, duration_seconds=120)
                base["source_rows"] = len(source)
            base["mapping"] = dict(columns=mapping, units=units, positive_discharge=form.get("positive_discharge") == "1", filters=filters)
            if task == "sdu":
                for key, fallback in (("cycle", form.get("cycle", "1")), ("phase_code", form.get("phase_code", "0"))):
                    if key not in frame:
                        frame[key] = pd.to_numeric(fallback, errors="raise")
                if "battery" not in frame:
                    frame["battery"] = profile["battery_id"]
    base["rows"] = len(frame)
    if task == "bms":
        frame = bms_validator(frame)
        base["checks"] = [dict(label="Cửa sổ BMS", status="Đạt", detail="Đủ đầu sạc 120 giây; SOC, điện áp, dòng điện và nhiệt độ hợp lệ.")]
    elif task == "sdu":
        schema, cycles, issue = audit_frame(frame)
        base["schema"] = schema.to_dict("records")
        base["checks"] = [dict(label="Chu kỳ " + str(r.cycle), status="Đạt" if r.status == "Hợp lệ" else "Không đạt", detail=r.error or "Đủ tín hiệu đầu xả để trích xuất đặc trưng.") for r in cycles.itertuples()]
        if issue or cycles.empty or (cycles.status != "Hợp lệ").any():
            base["scope"]["message"] = issue or "Cần sửa chu kỳ không hợp lệ trước khi dự đoán."
            return base, frame
        if cycles.phase_code.nunique() != 1 or cycles.battery.nunique() != 1 or len(cycles) != 1:
            raise ValueError("Mỗi hồ sơ cần một pin, một giai đoạn và một chu kỳ; lọc nhóm trước khi chạy.")
        base["cycle"] = int(cycles.cycle.iloc[0])
        base["phase_code"] = int(cycles.phase_code.iloc[0])
        base["source_battery_id"] = str(cycles.battery.iloc[0])
        if not sample and base["source_battery_id"] != profile["battery_id"]:
            base["warnings"].append("Mã trong dữ liệu (" + base["source_battery_id"] + ") khác mã hồ sơ (" + profile["battery_id"] + "). Kiểm tra lại trước khi đối chiếu lịch sử.")
    else:
        info = analyze(frame, profile)
        base["checks"] = [dict(label="Tín hiệu và thời gian", status="Đạt", detail="Bốn cột tín hiệu hữu hạn; thời gian tăng và không trùng.")]
        base["warnings"].extend(info["warnings"])
    if sample:
        base["warnings"].append("Mẫu minh họa đã tham gia học; không dùng kết quả này làm bằng chứng kiểm thử độc lập.")
    base.update(ready=True, preview=frame.head(5).to_dict("records"))
    return base, frame


def finalize(preflight, results, model, version, explanation=None, details=None):
    """Make one self-contained record; do not infer confidence from model fit."""
    record = {k: v for k, v in preflight.items() if k not in {"preview", "ready"}}
    task = record["task"]
    record.update(id=uuid4().hex, created_at=datetime.now(timezone.utc).isoformat(),
                  title=TASKS[task], results=results, model=model,
                  app_version=version, explanation=explanation, details=details,
                  limitation=LIMIT, uncertainty="Chưa có khoảng dự đoán được hiệu chuẩn cho từng hồ sơ. MAE kiểm thử không phải biên sai số của lần đo này.")
    record["next_steps"] = ["Đối chiếu mã pin, đơn vị và điều kiện đo trước khi sử dụng kết quả.",
                            "Muốn xác nhận dung lượng: thực hiện phép đo xả đầy đủ theo quy trình và điều kiện đối chiếu.",
                            "Chỉ so sánh lịch sử cùng pin, nguồn nhãn, mô hình, giai đoạn và điều kiện đo."]
    if task in {"sdu", "bms"}:
        path = MODELS[model] if task == "sdu" else "bms/" + ("random_forest.joblib" if model == "Random Forest" else "ridge_residual_forest.joblib")
        record["model_sha256"] = model_digest(path)
        record["label_source"] = "Dung lượng xả tham chiếu SDU" if task == "sdu" else "SOH suy ra từ dòng điện/SOC; chưa có RPT độc lập"
        metrics = evaluation_metrics() if task == "sdu" else table("reports/bms/metrics_summary.csv")
        chosen = metrics[metrics.model == model]
        record["validation"] = chosen.to_dict("records")
        if any(r.get("outside_count", 0) for r in results):
            record["warnings"].append("Có đặc trưng ngoài khoảng huấn luyện. Kết quả cần kiểm chứng riêng, không dùng làm kết luận về pin.")
    else:
        record["label_source"] = "Tỷ lệ hai phép đo dung lượng do người dùng cung cấp" if task == "capacity" else "Tín hiệu đo; không dự đoán SOH"
        record["uncertainty"] = ("Chưa cung cấp độ không đảm bảo của thiết bị và phép đo; không tự gán khoảng sai số."
                                 if task == "capacity" else "Chỉ tổng hợp tín hiệu đo; chưa áp dụng mô hình SOH cho cấu hình này.")
    if any(r.get("soh_pct") is not None and r["soh_pct"] > 100 for r in results):
        record["warnings"].append("SOH trên 100%: kiểm tra mốc dung lượng, điều kiện đo và miền mô hình; không quy đổi thành mức chai âm.")
    return record


from functools import lru_cache


@lru_cache(maxsize=16)
def _digest(path, mtime_ns, size):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_digest(relative):
    path = ROOT / "artifacts" / relative
    stat = path.stat()
    return _digest(path, stat.st_mtime_ns, stat.st_size)


def report_html(record):
    """Escaped, standalone report; browser printing provides a PDF export."""
    def text(value):
        return escape(str(value if value is not None else "Chưa có"))
    def rows(data):
        return "".join("<tr><th>" + text(k) + "</th><td>" + text(v) + "</td></tr>" for k, v in data)
    profile = record["profile"]
    profile_names = {"battery_id":"Mã pin/xe", "measured_at":"Ngày đo", "conditions":"Điều kiện đo", "chemistry":"Hóa học pin", "level":"Cấp đo", "mode":"Chế độ", "origin":"Nguồn dữ liệu", "nominal_ah":"Dung lượng định mức (Ah)"}
    parts = ["<h1>Hồ sơ đánh giá pin · Vincent D</h1>", "<h2>" + text(record["title"]) + "</h2>",
             "<table>" + rows((profile_names[k], v) for k,v in profile.items()) + "</table>",
             "<p>" + text(record["scope"]["message"]) + "</p>",
             "<h2>Kết quả</h2><table>" + rows(("SOH (%)", r.get("soh_pct")) for r in record["results"]) + "</table>",
             "<table>" + rows(("Mức chai (%)", r.get("loss_pct")) for r in record["results"]) + rows(("Dung lượng (Ah)",r.get("capacity_ah")) for r in record["results"]) + "</table>"]
    signals = record.get("signals", [])
    if signals:
        time_key = "time_s" if record["task"] == "bms" else "time"
        channels = [("pack_voltage", "Điện áp bộ pin (V)"), ("charge_current", "Dòng sạc (A)"), ("max_temperature", "Nhiệt độ cao nhất (°C)")] if time_key == "time_s" else [("terminal_voltage", "Điện áp (V)"), ("terminal_current", "Dòng điện (A)"), ("temperature", "Nhiệt độ (°C)")]
        for key, label in channels:
            points = [(float(r[time_key]), float(r[key])) for r in signals]
            x0, x1 = min(x for x, _ in points), max(x for x, _ in points)
            y0, y1 = min(y for _, y in points), max(y for _, y in points)
            coords = " ".join(f"{50+650*(x-x0)/max(x1-x0,1e-12):.2f},{175-140*(y-y0)/max(y1-y0,1e-12):.2f}" for x,y in points)
            parts.append('<h2>'+label+'</h2><svg viewBox="0 0 740 215" role="img" aria-label="'+label+'"><polyline fill="none" stroke="#13745a" stroke-width="2" points="'+coords+'"/><text x="50" y="20">'+text(f"{y0:.3f} – {y1:.3f}")+'</text><text x="50" y="205">'+text(f"Thời gian {x0:.1f} – {x1:.1f} giây")+'</text></svg>')
    for title, content in (("Kiểm tra dữ liệu", record["checks"]), ("Kết quả chi tiết", record["results"]), ("Đối chiếu kiểm thử", record.get("validation", [])), ("Giải thích mô hình", record.get("explanation")), ("Chi tiết phân tích", record.get("details"))):
        if content:
            parts.append("<h2>" + title + "</h2><pre>" + text(json.dumps(content, ensure_ascii=False, indent=2)) + "</pre>")
    parts += ["<h2>Giới hạn và bước tiếp theo</h2><p>" + text(record["uncertainty"]) + "</p><p>" + text(record["limitation"]) + "</p>",
              "<ul>" + "".join("<li>" + text(x) + "</li>" for x in record["warnings"] + record["next_steps"]) + "</ul>",
              "<h2>Truy xuất kết quả</h2><table>" + rows((k,record.get(k)) for k in ("id", "created_at", "source_name", "source_sha256", "filters", "model", "model_sha256", "app_version", "label_source")) + "</table>",
              "<p>File đầu vào và hồ sơ không được ứng dụng lưu trên máy chủ. Lịch sử trong trình duyệt có thể bị xóa; tự tải báo cáo để lưu trữ.</p>"]
    return '<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Báo cáo đánh giá pin</title><style>body{font:16px/1.6 system-ui;max-width:960px;margin:30px auto;padding:20px;color:#193834}table{width:100%;border-collapse:collapse}th,td{border:1px solid #ccc;text-align:left;padding:9px;overflow-wrap:anywhere}th{width:35%}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}h2{margin-top:30px}button{padding:12px}@media print{button{display:none}body{margin:0}tr{break-inside:avoid}}</style><button onclick="window.print()">In / Lưu PDF</button>' + "".join(parts) + '</html>'
