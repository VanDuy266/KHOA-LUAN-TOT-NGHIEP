"""Thực nghiệm nguồn độc lập và dự đoán riêng cho pin XJTU."""
import hashlib
import io
import json

import altair as alt
import joblib
import numpy as np
import pandas as pd
import streamlit as st
from app_data import ROOT, table, metadata
from components import heading, section, stat, csv_download, number
from charts import finish
from battery_soh.xjtu import normalized_features, read_cell

DESIGNS = {"XJTU held-out": "Giữ riêng pin XJTU", "SDU to XJTU": "Chuyển từ SDU sang XJTU",
           "Held-out batch 1": "Giữ riêng Batch-1", "Held-out batch 2": "Giữ riêng Batch-2"}
MODELS = {"Mean baseline": "Mốc trung bình", "Ridge": "Ridge", "Random Forest": "Random Forest",
          "LightGBM": "LightGBM", "GRU": "GRU", "Ridge-RF residual": "Ridge–RF phần dư",
          "RF multi-source": "RF đa nguồn", "RF normalized": "RF SDU · 11 đặc trưng chuẩn hóa",
          "RF original SDU": "RF SDU nguyên bản"}


def result_table(frame):
    result = frame.copy()
    if "model" in result:
        result["model"] = result.model.map(MODELS).fillna(result.model)
    if "design" in result:
        result["design"] = result.design.map(DESIGNS).fillna(result.design)
    return result.rename(columns={"model": "Mô hình", "design": "Thiết kế", "mae": "MAE (điểm %)",
                                  "rmse": "RMSE (điểm %)", "r2": "R²", "battery": "Mã pin",
                                  "batch": "Nhóm", "cycle": "Chu kỳ", "soh_pct": "SOH tham chiếu (%)",
                                  "prediction": "SOH dự đoán (%)", "outside_features": "Số đặc trưng ngoài miền"})


def render():
    heading("THỰC NGHIỆM / NGUỒN ĐỘC LẬP", "Pin Lishen XJTU", "NCM 18650 · 2 Ah · Batch-1 và Batch-2")
    if not (ROOT / "reports/xjtu/metrics_summary.csv").exists():
        st.info("Kết quả XJTU chưa được nạp.")
        return
    info = metadata("reports/xjtu/dataset_summary.json")
    for col, title, value, detail in zip(st.columns(4), ["PIN THÍ NGHIỆM", "ĐIỂM ĐO GỐC", "CHU KỲ HỢP LỆ", "DUNG LƯỢNG"],
        [number(info["batteries"]), number(info["raw_points"]), number(info["valid_cycles"]), "2 Ah"],
        ["23 trong 55 pin của nguồn", "Chỉ hai batch được chọn", "Đầu xả 120 giây", "SOH theo dung lượng danh định"]):
        with col:
            stat(title, value, detail)
    st.caption("Dữ liệu phòng thí nghiệm độc lập với SDU. Chưa kiểm chứng trên xe thực tế; hai nguồn có dòng xả và dung lượng khác nhau.")
    mode = st.radio("Nội dung", ["Kết quả kiểm thử", "Dự đoán XJTU", "Nguồn và chất lượng"], horizontal=True, key="xjtu_mode")
    data = table("reports/xjtu/features.csv")
    data = data.loc[data.cycle > 1].copy()
    if mode == "Kết quả kiểm thử":
        section("01", "So sánh trên pin chưa được học", "Trung bình không trọng số theo từng pin")
        summary = table("reports/xjtu/metrics_summary.csv")
        design = st.selectbox("Thiết kế đánh giá", list(DESIGNS), format_func=DESIGNS.get, key="xjtu_design")
        selected = summary[summary.design == design]
        st.dataframe(result_table(selected).round(3), hide_index=True, width="stretch")
        if design == "XJTU held-out":
            st.caption("Không dùng chu kỳ đầu 0,2C trong đánh giá chính. 5 vòng giữ riêng mã pin. RF đa nguồn học từ SDU và các pin XJTU thuộc tập học; tổng trọng số mỗi nguồn bằng nhau. Không dùng nhãn pin XJTU kiểm thử để học.")
        elif design == "SDU to XJTU":
            st.caption("Mô hình chỉ học từ SDU. Không học hoặc hiệu chỉnh bằng nhãn XJTU. RF 11 đặc trưng vừa chuẩn hóa dòng vừa bỏ giai đoạn; đây không phải phép thử riêng tác dụng chuẩn hóa. Sai số phản ánh giới hạn chuyển sang điều kiện khác.")
            with st.expander("Khác biệt miền đặc trưng"):
                st.dataframe(table("reports/xjtu/domain_shift.csv"), hide_index=True, width="stretch")
        else:
            st.caption("Toàn bộ pin của một batch được giữ để kiểm tra; mô hình chỉ học từ batch còn lại.")
        model_name = st.selectbox("Mô hình", selected.model.tolist(), format_func=MODELS.get, key="xjtu_result_model")
        prediction = table("reports/xjtu/predictions.csv")
        part = prediction[(prediction.design == design) & (prediction.model == model_name)]
        battery = st.selectbox("Mã pin", sorted(part.battery.unique()), key="xjtu_battery")
        plotted = part[part.battery == battery].sort_values("cycle")
        chart_data = plotted.melt(id_vars="cycle", value_vars=["actual_soh", "predicted_soh"], var_name="kind", value_name="soh")
        chart_data["kind"] = chart_data.kind.map({"actual_soh": "SOH tham chiếu", "predicted_soh": "SOH dự đoán"})
        chart = alt.Chart(chart_data).mark_line().encode(x=alt.X("cycle:Q", title="Chu kỳ"),
            y=alt.Y("soh:Q", title="SOH (%)", scale=alt.Scale(zero=False)), color=alt.Color("kind:N", title=""),
            tooltip=["cycle:Q", "kind:N", alt.Tooltip("soh:Q", format=".3f")])
        st.altair_chart(finish(chart), width="stretch", theme=None)
        csv_download("Tải kết quả pin", plotted, "xjtu_kiem_thu_theo_pin.csv")
        csv_download("Tải bảng so sánh", result_table(summary), "xjtu_so_sanh_mo_hinh.csv")
    elif mode == "Dự đoán XJTU":
        section("01", "Dự đoán theo chu kỳ", "Mô hình riêng cho dữ liệu XJTU; dòng điện được đổi sang C-rate")
        model_name = st.selectbox("Mô hình dự đoán", ["Random Forest", "RF multi-source"], format_func=MODELS.get, key="xjtu_predict_model")
        origin = st.radio("Đầu vào", ["Pin trong bộ dữ liệu", "File MAT XJTU"], horizontal=True, key="xjtu_input_origin")
        uploaded = None
        batch = 1
        if origin == "Pin trong bộ dữ liệu":
            battery = st.selectbox("Pin", sorted(data.battery.unique()), key="xjtu_demo_battery")
            st.caption("Pin này có trong dữ liệu refit mô hình ứng dụng. Dự đoán tại đây là minh họa; điểm kiểm thử độc lập nằm ở mục Kết quả kiểm thử.")
            request_key = f"{model_name}|{battery}"
        else:
            uploaded = st.file_uploader("MAT nguyên gốc Batch-1/2 · tối đa 128 MiB", type=["mat"], key="xjtu_mat")
            batch = st.selectbox("Nhóm thí nghiệm", [1, 2], key="xjtu_upload_batch")
            request_key = f"{model_name}|{batch}|" + (hashlib.sha256(uploaded.getbuffer()).hexdigest() if uploaded else "")
        if st.button("Dự đoán các chu kỳ", key="xjtu_predict", type="primary"):
            try:
                if origin == "Pin trong bộ dữ liệu":
                    frame = data[data.battery == battery].copy()
                else:
                    if uploaded is None:
                        raise ValueError("Chưa có file MAT đầu vào")
                    if uploaded.size > 128 * 1024 * 1024:
                        raise ValueError("File vượt giới hạn 128 MiB")
                    with st.spinner("Đang đọc chu kỳ XJTU…"):
                        frame, _, _, rejected, audit = read_cell(io.BytesIO(uploaded.getvalue()), "XJTU_UPLOAD", batch)
                    frame = frame.loc[frame.cycle > 1].copy()
                    if frame.empty:
                        raise ValueError("Không có chu kỳ xả 1C hợp lệ sau chu kỳ tham chiếu đầu tiên")
                    if rejected:
                        st.warning(f"Có {len(rejected)} chu kỳ không hợp lệ, không dự đoán.")
                    source_manifest = metadata("reports/xjtu/source_manifest.json")
                    digest = hashlib.sha256(uploaded.getbuffer()).hexdigest()
                    if any(item["sha256"] == digest for item in source_manifest["files"]):
                        st.info("File thuộc các pin đã dùng refit mô hình ứng dụng; kết quả này không phải kiểm thử độc lập.")
                filename = "random_forest.joblib" if model_name == "Random Forest" else "multi_source_forest.joblib"
                fitted = joblib.load(ROOT / "artifacts/xjtu" / filename)
                features = normalized_features(frame, 2.0)
                frame["prediction"] = fitted["model"].predict(features)
                lower = pd.Series(fitted["training_min"])
                upper = pd.Series(fitted["training_max"])
                frame["outside_features"] = ((features < lower - 1e-9) | (features > upper + 1e-9)).sum(axis=1)
                st.session_state["xjtu_prediction"] = (request_key, frame[["battery", "cycle", "soh_pct", "prediction", "outside_features"]])
            except (ValueError, KeyError, TypeError, OSError) as error:
                st.error(f"Không xử lý được dữ liệu: {error}")
        stored = st.session_state.get("xjtu_prediction")
        if stored is not None and stored[0] == request_key:
            st.dataframe(result_table(stored[1]).round(3), hide_index=True, width="stretch")
            csv_download("Tải kết quả dự đoán XJTU", result_table(stored[1]), "xjtu_du_doan.csv")
            st.caption("SOH tham chiếu đọc từ dung lượng xả trong nguồn, không được đưa vào đặc trưng dự đoán. Ngoài miền là cảnh báo phạm vi, không phải kết luận pin hỏng.")
    else:
        section("01", "Nguồn dữ liệu", "XJTU · công bố năm 2024 · CC BY 4.0")
        st.link_button("Nguồn XJTU trên Zenodo", "https://zenodo.org/records/10963339")
        st.write("Lishen 18650 NCM, dung lượng 2 Ah; SOH = dung lượng xả / 2 Ah × 100. Chọn 23 pin có quy trình cố định; không gộp các nhóm dòng biến thiên, xả một phần hoặc mô phỏng vệ tinh.")
        st.write(f"Chu kỳ bị loại: {number(info['excluded_cycles'])}. Phép đo cùng giây được gộp ở cửa sổ dẫn xuất: {number(info['duplicate_window_seconds_aggregated'])}. File MAT gốc được giữ nguyên.")
        st.dataframe(table("reports/xjtu/data_audit.csv").rename(columns={"battery":"Mã pin","batch":"Nhóm", "source_cycles":"Chu kỳ gốc", "raw_points":"Điểm đo gốc", "valid_cycles":"Chu kỳ hợp lệ", "excluded_cycles":"Chu kỳ bị loại", "duplicate_window_seconds_aggregated":"Mẫu cùng giây được gộp"}), hide_index=True, width="stretch")
        csv_download("Tải bảng đặc trưng XJTU", data, "xjtu_dac_trung_chu_ky.csv")
