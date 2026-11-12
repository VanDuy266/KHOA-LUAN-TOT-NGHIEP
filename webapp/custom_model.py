"""Portable numerical Ridge models; never deserialize executable model files."""
import hashlib
import io
import json
import math

import numpy as np
import pandas as pd
from battery_soh.features import FEATURES


def domain_profile(value):
    if not isinstance(value, dict):
        raise ValueError("Cần khai báo cấu hình và quy trình của dữ liệu huấn luyện.")
    for key, allowed in (("chemistry", {"NMC","LFP","LCO","NCA","LTO","other"}),
                         ("level", {"cell","pack"}), ("mode", {"charge","discharge","mixed"})):
        if value.get(key) not in allowed:
            raise ValueError("Khai báo hóa học pin, cấp đo và chế độ đo trước khi xuất mô hình dùng lại.")
    nominal = value.get("nominal_ah")
    try:
        nominal = float(nominal)
    except (ValueError, TypeError):
        raise ValueError("Dung lượng định mức cần là số Ah.")
    if not math.isfinite(nominal) or nominal <= 0:
        raise ValueError("Dung lượng định mức cần hữu hạn và lớn hơn 0.")
    protocol = value.get("protocol")
    if not isinstance(protocol, str) or not 10 <= len(protocol.strip()) <= 300:
        raise ValueError("Ghi quy trình trích xuất đặc trưng / đơn vị / cửa sổ đo (10–300 ký tự).")
    return dict(chemistry=value["chemistry"], level=value["level"], mode=value["mode"], nominal_ah=nominal, protocol=protocol.strip())


def export_ridge(pipeline, train, report, domain=None):
    scaler, ridge = pipeline.steps[0][1], pipeline.steps[-1][1]
    return dict(format="vincent-ridge", version=1, features=FEATURES,
                mean=scaler.mean_.tolist(), scale=scaler.scale_.tolist(),
                coefficients=ridge.coef_.tolist(), intercept=float(ridge.intercept_),
                training_min=train[FEATURES].min().tolist(), training_max=train[FEATURES].max().tolist(),
                train_batteries=report["train_batteries"], test_batteries=report["test_batteries"],
                n_train=report["n_train"], n_test=report["n_test"], source_sha256=report["source_sha256"],
                label_source=report["label_source"], domain=domain,
                validation=next(score for score in report["scores"] if score["model"] == "Ridge"),
                scope="Mô hình Ridge chỉ học trên các nhóm train; nhóm test giữ riêng. Dùng thử nghiệm trong cấu hình và quy trình đã khai báo, chưa chứng minh trên pin/xe mới ngoài nguồn.")


def predict_portable(model, raw, declared_domain):
    if not isinstance(model, dict) or model.get("format") != "vincent-ridge" or model.get("version") != 1 or model.get("features") != FEATURES:
        raise ValueError("Chỉ nhận mô hình Ridge JSON phiên bản 1 do chức năng huấn luyện xuất ra; không nhận joblib/pickle.")
    domain = domain_profile(model.get("domain"))
    if domain_profile(declared_domain) != domain:
        raise ValueError("Cấu hình và quy trình dữ liệu mới phải khớp hồ sơ của mô hình.")
    arrays = {}
    for key in ("mean", "scale", "coefficients", "training_min", "training_max"):
        try:
            value = np.asarray(model.get(key), dtype=float)
        except (TypeError, ValueError):
            raise ValueError("Tham số mô hình cần là mảng số.")
        if value.shape != (len(FEATURES),) or not np.isfinite(value).all():
            raise ValueError("Tham số mô hình sai kích thước hoặc không hữu hạn.")
        arrays[key] = value
    if (arrays["scale"] <= 0).any() or (arrays["training_min"] > arrays["training_max"]).any():
        raise ValueError("Thang chuẩn hóa hoặc miền huấn luyện không hợp lệ.")
    intercept = model.get("intercept")
    if isinstance(intercept, bool) or not isinstance(intercept, (int, float)) or not math.isfinite(intercept):
        raise ValueError("Hệ số chặn không hợp lệ.")
    groups = model.get("train_batteries")
    if not isinstance(groups, list) or not 1 <= len(groups) <= 200 or not all(isinstance(x, str) and len(x) <= 100 for x in groups):
        raise ValueError("Danh sách pin train không hợp lệ.")
    data = pd.read_csv(io.BytesIO(raw), nrows=5001)
    if not 1 <= len(data) <= 5000 or len(data.columns) > 30:
        raise ValueError("Dữ liệu mới cần 1–5.000 dòng, tối đa 30 cột.")
    if set(["battery", *FEATURES])-set(data):
        raise ValueError("CSV mới cần battery và đủ 12 cột đặc trưng như lúc huấn luyện; không cần nhãn soh_pct.")
    if data.battery.isna().any() or data.battery.astype(str).str.strip().eq("").any():
        raise ValueError("Mỗi dòng cần mã pin.")
    x = data[FEATURES].apply(pd.to_numeric, errors="raise").to_numpy(dtype=float)
    if not np.isfinite(x).all() or not np.isin(x[:,0], [0,1]).all() or (x[:,1] < 1).any() or (x[:,1] % 1 != 0).any():
        raise ValueError("Đặc trưng phải hữu hạn; phase_code 0/1, cycle nguyên dương.")
    with np.errstate(over="ignore", invalid="ignore"):
        contributions = ((x-arrays["mean"])/arrays["scale"])*arrays["coefficients"]
        predictions = contributions.sum(axis=1)+intercept
    outside = ((x < arrays["training_min"]) | (x > arrays["training_max"]))
    rows = []
    for index, (row, prediction) in enumerate(zip(data.itertuples(), predictions)):
        accepted = math.isfinite(float(prediction)) and 0 <= prediction <= 130
        rows.append(dict(battery=str(row.battery), cycle=int(row.cycle), phase_code=int(row.phase_code),
                         predicted_soh_pct=float(prediction) if accepted else None,
                         status="Dự đoán thử nghiệm" if accepted else "Không xuất dự đoán: ngoài 0–130% hoặc không hữu hạn",
                         seen_in_training=str(row.battery) in groups, outside_count=int(outside[index].sum())))
    encoded = json.dumps(model, sort_keys=True, ensure_ascii=False).encode()
    return dict(results=rows, model_sha256=hashlib.sha256(encoded).hexdigest(), input_sha256=hashlib.sha256(raw).hexdigest(),
                domain=domain, source="Tính trực tiếp từ CSV mới và tham số Ridge JSON bạn cung cấp.",
                scope="Tham số và kết quả kiểm thử trong file mô hình chưa được xác thực. Cùng cấu hình khai báo chưa chứng minh khả năng tổng quát hóa. Không kết luận pin hỏng/an toàn.",
                explanation=dict(baseline=float(intercept), effects=[dict(feature=f,contribution=float(v)) for f,v in zip(FEATURES,contributions[0])]) if len(rows)==1 and rows[0]["predicted_soh_pct"] is not None else None)


def extract_features(raw):
    """Build the documented 120-second statistics from each uploaded group."""
    from prediction import normalize_columns
    data = normalize_columns(pd.read_csv(io.BytesIO(raw), nrows=100001))
    signals = ["time", "terminal_voltage", "terminal_current", "temperature"]
    required = ["battery", "cycle", "phase_code", *signals]
    if not set(required) <= set(data):
        raise ValueError("CSV tín hiệu cần battery, cycle, phase_code, time, terminal_voltage, terminal_current, temperature.")
    if not 5 <= len(data) <= 100000:
        raise ValueError("CSV tín hiệu cần 5–100.000 dòng.")
    if data.battery.isna().any() or data.battery.astype(str).str.strip().eq("").any():
        raise ValueError("Dòng tín hiệu cần mã pin.")
    data["battery"] = data.battery.astype(str).str.strip()
    for key in ["cycle", "phase_code", *signals] + (["soh_pct"] if "soh_pct" in data else []):
        data[key] = pd.to_numeric(data[key], errors="raise")
        if not np.isfinite(data[key].to_numpy()).all():
            raise ValueError("Tín hiệu hoặc nhãn thiếu/không hữu hạn: " + key)
    if not data.phase_code.isin([0,1]).all() or (data.cycle < 1).any() or (data.cycle % 1 != 0).any():
        raise ValueError("phase_code cần 0/1 và cycle nguyên dương.")
    groups = data.groupby(["battery", "phase_code", "cycle"], sort=False)
    if groups.ngroups > 5000:
        raise ValueError("Tối đa 5.000 nhóm pin/giai đoạn/chu kỳ.")
    rows = []
    for (battery, phase, cycle), group in groups:
        group = group.sort_values("time").copy()
        if (group.time < 0).any() or group.time.duplicated().any():
            raise ValueError(f"{battery}, chu kỳ {cycle}: thời gian âm hoặc trùng.")
        group["time"] -= group.time.iloc[0]
        window = group[group.time <= 120]
        active = window[window.terminal_current.abs() > .1]
        if len(window) < 5 or window.time.max() < 90 or len(active) < 3 or active.time.max()-active.time.min() < 30:
            raise ValueError(f"{battery}, chu kỳ {cycle}: chưa đủ cửa sổ đầu 120 giây hoặc mẫu có dòng điện.")
        if (active.terminal_voltage <= 0).any() or not active.temperature.between(-80,150).all():
            raise ValueError(f"{battery}, chu kỳ {cycle}: kiểm tra điện áp và đơn vị nhiệt độ.")
        t = active.time.to_numpy(); centered = t-t.mean()
        def slope(column):
            values = active[column].to_numpy()
            return float(np.dot(centered,values-values.mean())/np.dot(centered,centered))
        row = dict(battery=battery, phase_code=int(phase), cycle=int(cycle),
                   voltage_mean=float(active.terminal_voltage.mean()), voltage_min=float(active.terminal_voltage.min()),
                   voltage_max=float(active.terminal_voltage.max()), voltage_std=float(active.terminal_voltage.std(ddof=0)), voltage_slope=slope("terminal_voltage"),
                   current_mean=float(active.terminal_current.mean()), current_std=float(active.terminal_current.std(ddof=0)),
                   temperature_mean=float(active.temperature.mean()), temperature_max=float(active.temperature.max()), temperature_slope=slope("temperature"))
        if "soh_pct" in group:
            if group.soh_pct.nunique() != 1 or not group.soh_pct.between(0,130).all():
                raise ValueError(f"{battery}, chu kỳ {cycle}: nhãn SOH cần nhất quán và trong 0–130%.")
            row["soh_pct"] = float(group.soh_pct.iloc[0])
        rows.append(row)
    result = pd.DataFrame(rows)
    return dict(rows=rows, csv=result.to_csv(index=False), has_labels="soh_pct" in result,
                input_sha256=hashlib.sha256(raw).hexdigest(),
                method="Thống kê trong 120 giây đầu từng nhóm, dùng mẫu |I| > 0,1 A, độ lệch chuẩn ddof=0 và độ dốc OLS theo giây. Cần cùng cách trích xuất khi huấn luyện và dự đoán; nhãn chỉ được giữ riêng, không đưa vào đặc trưng.")
