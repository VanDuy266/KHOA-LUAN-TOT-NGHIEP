"""HTTP application: real HTML pages and JSON APIs, without a Streamlit runtime."""
import sys
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app"))

from functools import lru_cache
from threading import BoundedSemaphore
from urllib.parse import urlsplit
import gzip
import hashlib
import io
import json
import math
import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request, send_file, abort
from werkzeug.exceptions import HTTPException
from webapp.data import table, metadata, artifact, cycle_measurements, PHASES, MODELS, evaluation_results
from webapp.bms_assessment import assess as assess_bms, read_limits
from prediction import read_csv, predict_batch, predict
from input_audit import audit_frame
from explanation import prediction_contributions
from labels import MODEL_NAMES, COLUMNS
from battery_soh.features import FEATURES
from battery_soh.bms import FEATURES as BMS_FEATURES, charging_features

app = Flask(__name__)
app.json.sort_keys = False
app.config.update(MAX_CONTENT_LENGTH=20 * 1024 * 1024, MAX_FORM_MEMORY_SIZE=1024 * 1024)
INFERENCE = BoundedSemaphore(1)
TITLE = "Vincent D | Phân tích sức khỏe pin xe điện"


def clean(value):
    if isinstance(value, pd.DataFrame):
        return json.loads(value.to_json(orient="records", date_format="iso"))
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def reply(**values):
    return jsonify(clean(values))


def integer(name, default, minimum=1):
    raw = request.values.get(name, default)
    try:
        value = int(raw)
    except (ValueError, TypeError):
        raise ValueError(f"{name}: cần số nguyên hợp lệ.")
    if value < minimum:
        raise ValueError(f"{name}: giá trị phải từ {minimum} trở lên.")
    return value


def stage():
    phase = request.args.get("phase", "primary")
    if phase not in PHASES:
        raise ValueError("Giai đoạn không hợp lệ.")
    return phase


def downsample(frame, size=400):
    return frame.iloc[np.unique(np.linspace(0, len(frame)-1, min(size, len(frame))).astype(int))] if len(frame) else frame


def display(frame):
    result = frame.copy()
    if "model" in result:
        result["model"] = result.model.map(MODEL_NAMES).fillna(result.model)
    return result.rename(columns=COLUMNS)


def uploaded():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        raise ValueError("Bạn chưa chọn file CSV.")
    if not upload.filename.lower().endswith((".csv", ".csv.gz", ".gz")):
        raise ValueError("Chỉ nhận CSV hoặc CSV.GZ.")
    raw = upload.read(20 * 1024 * 1024 + 1)
    if len(raw) > 20 * 1024 * 1024:
        abort(413)
    if raw[:2] == b"\x1f\x8b":
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as source:
            raw = source.read(50 * 1024 * 1024 + 1)
        if len(raw) > 50 * 1024 * 1024:
            raise ValueError("Dữ liệu giải nén vượt giới hạn 50 MiB.")
    return raw


def input_frame():
    phase = integer("phase_code", 0, 0)
    if phase not in (0, 1):
        raise ValueError("Giai đoạn phải là 0 hoặc 1.")
    if request.form.get("sample") == "1":
        data = table("data/clean/sample_measurements.csv")
        return data[(data.battery == "SDU_01") & (data.phase_code == phase) & (data.cycle == 1) & (data.time <= 120)].copy()
    frame = read_csv(uploaded(), phase_code=phase)
    if "cycle" not in frame:
        frame["cycle"] = integer("cycle", 1)
    return frame


@app.before_request
def same_origin():
    if request.method == "POST" and request.headers.get("Origin"):
        origin = urlsplit(request.headers["Origin"])
        if origin.netloc != request.host:
            abort(403, "Yêu cầu phải được gửi từ chính trang web này.")


@app.after_request
def headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(Exception)
def errors(error):
    if isinstance(error, HTTPException):
        message = "File vượt giới hạn tải lên 20 MiB." if error.code == 413 else error.description
        return jsonify(error=message), error.code
    if isinstance(error, (ValueError, TypeError, KeyError, UnicodeError, OSError, EOFError, pd.errors.ParserError)):
        return jsonify(error=str(error)), 400
    app.logger.exception("HTTP request failed")
    return jsonify(error="Không xử lý được yêu cầu. Vui lòng thử lại hoặc kiểm tra nhật ký máy chủ."), 500


@app.get("/")
def home():
    return render_template("index.html", title=TITLE, version=hashlib.sha256(b"".join((ROOT / name).read_bytes() for name in ("webapp/static/app.js", "webapp/static/app.css", "webapp/templates/index.html"))).hexdigest()[:12])


@app.get("/healthz")
@app.get("/_stcore/health")
def health():
    # Keep the old health path working on the existing Render service.
    return "ok", 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.get("/api/version")
def version():
    return reply(runtime="Flask", commit=os.environ.get("RENDER_GIT_COMMIT", "local"),
        frontend=hashlib.sha256((ROOT/"webapp/static/app.js").read_bytes()).hexdigest()[:12])


@app.get("/assets/logo.png")
@app.get("/favicon.ico")
def logo():
    return send_file(ROOT / "app/assets/vincent-d-logo-avatar.png", mimetype="image/png", max_age=86400)


@app.get("/api/overview")
def overview():
    data = table("reports/features.csv")
    phase = stage()
    selected = data[data.phase == phase]
    stats = selected.groupby("battery").agg(cycles=("cycle", "count"), soh_min=("soh_pct", "min"), soh_max=("soh_pct", "max")).reset_index()
    metrics = evaluation_results()[0]
    best = metrics.sort_values("mae").iloc[0]
    return reply(dataset=metadata("reports/dataset_summary.json"), phase=phase, phases=PHASES,
        batteries=sorted(selected.battery.unique()), stats=stats,
        kpis=[dict(label="Pin thử nghiệm", value=int(data.battery.nunique()), detail="Cell SDU · NMC(532)/graphite"),
              dict(label="Chu kỳ xả", value=len(data), detail="Hai giai đoạn sử dụng"),
              dict(label="SOH trung vị", value=round(float(data.soh_pct.median()),2), unit="%", detail="Dung lượng xả / 2,4 Ah"),
              dict(label="MAE · " + MODEL_NAMES.get(best.model, best.model), value=round(float(best.mae),3), detail="Điểm % SOH · kiểm thử giữ riêng pin")],
        model_count=len(metrics))


@app.get("/api/trends")
def trends():
    data = table("reports/features.csv")
    phase = stage()
    selected = data[data.phase == phase]
    pins = request.args.get("batteries", ",".join(sorted(selected.battery.unique())[:4])).split(",")
    if len(pins) > 6 or any(pin not in set(selected.battery) for pin in pins):
        raise ValueError("Chọn từ 1 đến 6 mã pin hợp lệ.")
    return reply(series=[dict(name=pin, points=downsample(selected[selected.battery==pin].sort_values("cycle"))[["cycle","soh_pct"]]) for pin in pins])


@app.get("/api/explorer")
def explorer():
    phase = stage()
    data = table("reports/features.csv")
    part = data[data.phase==phase]
    pins = sorted(part.battery.unique())
    pin = request.args.get("battery", pins[0])
    if pin not in pins:
        raise ValueError("Mã pin không hợp lệ.")
    selected = part[part.battery==pin].sort_values("cycle")
    cycle = integer("cycle", int(selected.cycle.iloc[0]))
    if cycle not in set(selected.cycle):
        raise ValueError("Chu kỳ không có trong pin và giai đoạn đã chọn.")
    raw = cycle_measurements(pin, cycle, phase)
    if request.args.get("full") != "1":
        raw = raw[raw.time<=120]
    return reply(batteries=pins, battery=pin, cycles=selected.cycle.astype(int).tolist(), cycle=cycle,
        summary=selected[selected.cycle==cycle].iloc[0].to_dict(), trend=downsample(selected)[["cycle","soh_pct"]],
        signals=downsample(raw,800), measurement_count=len(raw))


@app.get("/api/evaluation")
def evaluation():
    metrics, by_battery, predictions, phases, timings = evaluation_results()
    names=metrics.model.tolist()
    name=request.args.get("model", names[0])
    if name not in names:
        raise ValueError("Mô hình không hợp lệ.")
    part=predictions[predictions.model==name]
    pin=request.args.get("battery",sorted(part.battery.unique())[0])
    if pin not in set(part.battery):
        raise ValueError("Mã pin không hợp lệ.")
    shown=part[part.battery==pin].sort_values(["phase","cycle"])
    return reply(models=[dict(value=x,label=MODEL_NAMES.get(x,x)) for x in names], model=name,
        batteries=sorted(part.battery.unique()),battery=pin, metrics=display(metrics).round(5),
        by_battery=display(by_battery[by_battery.model==name]).round(5), phases=display(phases[phases.model==name]).round(5),
        timings=display(timings[timings.model==name]).round(5),
        series=[dict(name=PHASES[phase],points=downsample(p)[["cycle","actual_soh","predicted_soh"]]) for phase,p in shown.groupby("phase")])


@app.post("/api/forecast")
def forecast():
    name=request.form.get("model","Random Forest")
    if name not in MODELS:
        raise ValueError("Mô hình không hỗ trợ dự đoán.")
    with INFERENCE:
        fitted=artifact(MODELS[name])
        frame=input_frame()
        result=predict_batch(frame, fitted)
        explanation=None
        if len(result)==1 and result.status.iloc[0]=="Thành công":
            estimate,features,outside=predict(frame,int(result.cycle.iloc[0]),fitted)
            baseline,effects,method=prediction_contributions(fitted["model"],features)
            explanation=dict(baseline=baseline,effects=effects,method=method,features=features)
    return reply(model=name,results=result,explanation=explanation,sample=request.form.get("sample")=="1")


@app.post("/api/audit")
def audit():
    frame=input_frame()
    schema,checks,issue=audit_frame(frame)
    return reply(schema=schema,checks=checks,issue=issue,rows=len(frame),preview=frame.head(100))


@app.get("/api/demo")
def demo():
    with INFERENCE:
        fitted=artifact("random_forest_demo.joblib")
        if fitted["held_out_battery"] in fitted["batteries"]:
            raise ValueError("Pin kiểm thử trùng với tập học.")
        if fitted["data_sha256"] != feature_hash():
            raise ValueError("Dữ liệu không khớp mô hình demo.")
        data=table("reports/features.csv")
        selected=data[(data.battery==fitted["held_out_battery"]) & (data.phase==stage())].sort_values("cycle").copy()
        selected["predicted_soh_pct"]=fitted["model"].predict(selected[FEATURES])
    selected["absolute_error"]=(selected.soh_pct-selected.predicted_soh_pct).abs()
    return reply(battery=fitted["held_out_battery"],train_batteries=len(fitted["batteries"]),n_train=fitted["n_train"],
        mae=float(selected.absolute_error.mean()),results=selected[["battery","phase","cycle","soh_pct","predicted_soh_pct","absolute_error"]])


@app.post("/api/demo/predict")
def demo_predict():
    phase=request.form.get("phase","primary")
    if phase not in PHASES:
        raise ValueError("Giai đoạn không hợp lệ.")
    cycle=integer("cycle",1)
    with INFERENCE:
        fitted=artifact("random_forest_demo.joblib")
        pin=fitted["held_out_battery"]
        if pin in fitted["batteries"] or fitted["data_sha256"]!=feature_hash():
            raise ValueError("Mô hình hoặc dữ liệu demo không khớp thiết kế giữ riêng pin.")
        data=table("reports/features.csv")
        row=data[(data.battery==pin)&(data.phase==phase)&(data.cycle==cycle)]
        if len(row)!=1:
            raise ValueError("Chu kỳ không có trong pin demo và giai đoạn đã chọn.")
        features=row[FEATURES].copy()
        estimate=float(fitted["model"].predict(features)[0])
        baseline,effects,method=prediction_contributions(fitted["model"],features)
    reference=float(row.soh_pct.iloc[0])
    raw=cycle_measurements(pin,cycle,phase)
    return reply(battery=pin,phase=phase,cycle=cycle,prediction=estimate,reference=reference,
        absolute_error=abs(estimate-reference),train_batteries=len(fitted["batteries"]),
        features=features,baseline=baseline,effects=effects,method=method,
        signals=downsample(raw[raw.time<=120],300))


@lru_cache(maxsize=1)
def feature_hash():
    return hashlib.sha256((ROOT/"reports/features.csv").read_bytes()).hexdigest()


@app.get("/api/anomalies")
def anomalies():
    data=table("reports/anomaly_predictions.csv")
    pins=sorted(data.battery.unique())
    pin=request.args.get("battery",pins[0])
    if pin not in pins:
        raise ValueError("Mã pin không hợp lệ.")
    part=data[(data.battery==pin)&(data.phase==stage())].sort_values("cycle")
    return reply(batteries=pins,battery=pin,points=part,flagged=part[part.flag==True],summary=metadata("reports/anomaly_metadata.json"))


@app.get("/api/quality")
def quality():
    return reply(dataset=metadata("reports/dataset_summary.json"),audit=display(table("reports/data_audit.csv")),
        suspected=display(table("reports/suspected_measurements.csv")), removed=display(table("reports/removed_measurements.csv")))


@app.get("/api/bms")
def bms():
    data=table("reports/bms/features.csv")
    vehicles=sorted(data.vehicle.unique())
    vehicle=request.args.get("vehicle",vehicles[0])
    if vehicle not in vehicles:
        raise ValueError("Mã xe không hợp lệ.")
    sessions=data[data.vehicle==vehicle].sort_values("start")
    sid=integer("session",int(sessions.session.iloc[0]))
    if sid not in set(sessions.session):
        raise ValueError("Phiên sạc không thuộc xe đã chọn.")
    monthly=table("reports/bms/monthly_reference.csv")
    monthly=monthly[monthly.vehicle==vehicle].copy()
    monthly["soh_pct"]=monthly.reference_capacity_ah/145*100
    windows=pd.read_parquet(ROOT/"data/bms/processed/windows.parquet",filters=[("vehicle","=",vehicle),("session","=",sid)])
    name=request.args.get("model","Ridge-RF residual")
    if name not in {"Ridge-RF residual","Random Forest","Ridge","Mean baseline"}:
        raise ValueError("Mô hình BMS không hợp lệ.")
    held=table("reports/bms/predictions.csv")
    held=held[(held.vehicle==vehicle)&(held.model==name)]
    comparison=held.groupby("month")[["reference_soh_pct","prediction"]].mean().reset_index()
    return reply(dataset=metadata("reports/bms/dataset_summary.json"),vehicles=vehicles,vehicle=vehicle,session=sid,
        model=name, comparison=comparison,
        sessions=sessions[["session","start"]],monthly=monthly,signals=windows,
        metrics=display(table("reports/bms/metrics_summary.csv")).round(5),
        by_vehicle=display(table("reports/bms/metrics_by_vehicle.csv")).round(5),
        timings=display(table("reports/bms/timings.csv")).round(5))


def bms_signal_preview(window, limit=300):
    # Retain alert-relevant extremes even when a dense upload needs downsampling.
    indexes=set(np.linspace(0,len(window)-1,min(limit,len(window))).astype(int).tolist())
    for signal in (window.max_temperature, window.min_temperature, window.max_cell_voltage-window.min_cell_voltage):
        values=signal.to_numpy()
        indexes.update([int(np.argmax(values)),int(np.argmin(values))])
    return window.iloc[sorted(indexes)]


@app.post("/api/bms/predict")
def bms_predict():
    name=request.form.get("model","Random Forest")
    if name not in ("Random Forest","Ridge-RF residual"):
        raise ValueError("Mô hình BMS không hợp lệ.")
    limits=read_limits(request.form)
    source=dict(kind="upload",label="CSV tải lên")
    history=None
    if request.form.get("sample")=="1":
        vehicle=request.form.get("sample_vehicle")
        sid=request.form.get("sample_session")
        if vehicle or sid:
            if not vehicle or not sid:
                raise ValueError("Cần chọn đủ xe và phiên minh họa.")
            sid=integer("sample_session",1)
            candidates=table("reports/bms/features.csv")
            selected=candidates[(candidates.vehicle==vehicle)&(candidates.session==sid)]
            if len(selected)!=1:
                raise ValueError("Phiên minh họa không thuộc xe đã chọn.")
            record=selected.iloc[0]
            window=pd.read_parquet(ROOT/"data/bms/processed/windows.parquet",filters=[("vehicle","=",vehicle),("session","=",sid)])
            source=dict(kind="example",label="Phiên minh họa đã tham gia học lại mô hình",vehicle=vehicle,session=sid,start=str(record.start))
            reference=table("reports/bms/monthly_reference.csv")
            past=reference[(reference.vehicle==vehicle)&(reference.month.astype(str)<str(record.month))].sort_values("month").copy()
            past["soh_pct"]=past.reference_capacity_ah/145*100
            history=dict(points=clean(past[["month","soh_pct","reference_sessions"]]),
                message="Chỉ hiển thị các tháng trước tháng của phiên đang chọn; đây là nhãn suy ra từ vận hành.",
                delta_soh_pp=float(past.soh_pct.iloc[-1]-past.soh_pct.iloc[0]) if len(past)>=2 else None)
        else:
            window=table("data/bms/processed/01_example.csv.gz").copy()
            source=dict(kind="example",label="Phiên mẫu 01 đã tham gia học lại mô hình")
    else:
        if request.form.get("configuration")!="BAIC EU500 145Ah":
            raise ValueError("Cần xác nhận đúng cấu hình BAIC EU500, bộ pin 145 Ah.")
        window=pd.read_csv(io.BytesIO(uploaded()))
        upload=request.files.get("file")
        if upload and upload.filename:
            filename=upload.filename.replace("\\","/").split("/")[-1][:120]
            source.update(label="CSV tải lên · "+filename, filename=filename)
    required=['time_s','soc','pack_voltage','charge_current','max_cell_voltage','min_cell_voltage','max_temperature','min_temperature']
    if set(required)-set(window):
        raise ValueError("CSV thiếu cột: "+", ".join(sorted(set(required)-set(window))))
    window=window[required].apply(pd.to_numeric,errors="raise")
    if not np.isfinite(window.to_numpy()).all():
        raise ValueError("CSV chứa giá trị thiếu hoặc vô hạn.")
    delta=window.time_s.diff().dropna()
    if (delta<=0).any() or (delta>10).any() or window.empty or abs(window.time_s.iloc[0])>1e-6:
        raise ValueError("Thời gian phải bắt đầu từ 0, tăng đều và không gián đoạn quá 10 giây.")
    window=window[window.time_s<=120]
    if len(window)<12 or window.time_s.max()<112:
        raise ValueError("Chưa đủ cửa sổ đầu sạc 120 giây.")
    if not window.soc.between(0,100).all() or (window.soc.diff().dropna()<-.1).any() or (window.soc.diff().dropna()>2).any():
        raise ValueError("SOC phải trong 0–100% và không nhảy bất thường.")
    if not window.pack_voltage.between(200,450).all() or not window.charge_current.between(-300,0).all() or (window.charge_current<0).mean()<.95:
        raise ValueError("Điện áp bộ pin cần 200–450 V; dòng sạc âm trong khoảng −300 đến 0 A.")
    if not window.min_cell_voltage.between(2,4.5).all() or not window.max_cell_voltage.between(2,4.5).all() or (window.max_cell_voltage<window.min_cell_voltage).any():
        raise ValueError("Điện áp cell không hợp lệ.")
    if not window.min_temperature.between(-30,85).all() or not window.max_temperature.between(-30,85).all() or (window.max_temperature<window.min_temperature).any():
        raise ValueError("Nhiệt độ không hợp lệ.")
    with INFERENCE:
        fitted=artifact("bms/"+("random_forest.joblib" if name=="Random Forest" else "ridge_residual_forest.joblib"))
        features=pd.DataFrame([charging_features(window)])[BMS_FEATURES]
        outside=((features.iloc[0]<pd.Series(fitted['training_min']))|(features.iloc[0]>pd.Series(fitted['training_max'])))
        estimate=float(fitted['model'].predict(features)[0])
    outside_names=outside[outside].index.tolist()
    assessment=assess_bms(window,estimate,outside_names,limits,source,history)
    assessment["report_rows"].insert(0,{"Hạng mục":"Mô hình","Giá trị":name,"Đơn vị":"","Diễn giải":assessment["scope"]})
    assessment["report_rows"].insert(1,{"Hạng mục":"Nguồn đầu vào","Giá trị":source["label"],"Đơn vị":"","Diễn giải":str(source.get("vehicle",""))+" · "+str(source.get("session",""))})
    return reply(model=name,prediction=estimate,outside=outside_names,sample=request.form.get("sample")=="1",
        assessment=assessment,signals=bms_signal_preview(window))


@app.get("/api/download/sample")
def sample_download():
    if request.args.get("kind")=="bms":
        frame=table("data/bms/processed/01_example.csv.gz")
        frame=frame[frame.time_s<=120]
        name="bms_cua_so_120s.csv"
    else:
        frame=table("data/clean/sample_measurements.csv")
        frame=frame[(frame.battery=="SDU_01")&(frame.phase_code==0)&(frame.cycle==1)&(frame.time<=120)]
        name="mau_dinh_dang_sdu.csv"
    return send_csv(frame,name)


@app.get("/api/download/cycle")
def cycle_download():
    phase=stage()
    frame=cycle_measurements(request.args.get("battery","SDU_01"),integer("cycle",1),phase)
    return send_csv(frame,"tin_hieu_chu_ky.csv")


def send_csv(frame,name):
    return send_file(io.BytesIO(frame.to_csv(index=False).encode("utf-8-sig")),mimetype="text/csv; charset=utf-8",as_attachment=True,download_name=name)
