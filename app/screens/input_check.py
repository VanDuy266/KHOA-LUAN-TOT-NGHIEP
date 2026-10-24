"""Kiểm tra file người dùng, tách biệt kiểm toán bộ dữ liệu nghiên cứu."""

import hashlib
import pandas as pd
import streamlit as st
from app_data import table
from components import heading, csv_download
from input_audit import audit_frame
from labels import vietnamese_table
from prediction import read_csv


def render():
    heading("", "Kiểm tra file đầu vào", "Xem cấu trúc dữ liệu và lỗi từng chu kỳ trước khi dự đoán SOH.")
    upload = st.file_uploader("Chọn CSV hoặc CSV.GZ", type=["csv", "gz"], key="audit_upload")
    phase = st.selectbox("Giai đoạn nếu file chưa có phase_code", [0, 1], format_func=lambda value: "Sử dụng ban đầu" if value == 0 else "Tái sử dụng", key="audit_phase")
    sample = st.checkbox("Thử kiểm tra bằng dữ liệu mẫu", key="audit_sample", disabled=upload is not None)
    st.caption("CSV SDU gốc: hiển thị dữ liệu sau quy đổi về 120 giây đầu xả.")
    template = table("data/clean/sample_measurements.csv")
    template = template[(template.battery == "SDU_01") & (template.phase_code == 0) & (template.cycle == 1) & (template.time <= 120)]
    template = template[["battery", "cycle", "phase_code", "time", "terminal_voltage", "terminal_current", "temperature"]]
    csv_download("Tải mẫu định dạng CSV", template, "mau_dinh_dang.csv", key="audit_template")
    content = upload.getvalue() if upload is not None else None
    identity = (hashlib.sha256(content).hexdigest() if content is not None else None, phase, sample if content is None else False)
    analyze = st.button("Phân tích lại", type="primary", icon=":material/fact_check:")
    previous = st.session_state.get("input_audit_result")
    if analyze or (content is not None and (not previous or len(previous) != 8 or previous[0] != identity)):
        st.session_state.pop("input_audit_result", None)
        if content is None and not sample:
            st.error("Chọn file hoặc bật dữ liệu mẫu.")
        else:
            try:
                with st.spinner("Đang kiểm tra các chu kỳ..."):
                    frame = read_csv(content, phase_code=phase) if content is not None else template.copy()
                    schema, checks, issue = audit_frame(frame)
                source_name = upload.name if content is not None else "Dữ liệu mẫu SDU_01"
                phase_origin = "Từ lựa chọn trên giao diện" if frame.attrs.get("phase_from_selection") or frame.attrs.get("source_format") == "sdu_raw" else "Từ cột phase_code trong file"
                st.session_state["input_audit_result"] = (identity, frame.head(100), len(frame), schema, checks, issue, source_name, phase_origin)
            except (ValueError, TypeError, KeyError, OSError, EOFError, UnicodeDecodeError, pd.errors.ParserError) as error:
                st.error(str(error))
    result = st.session_state.get("input_audit_result")
    if not result or len(result) != 8 or result[0] != identity:
        return
    _, preview, count, schema, checks, issue, source_name, phase_origin = result
    st.write(f"File: {source_name}")
    st.caption(f"Giai đoạn: {phase_origin}")
    if issue:
        st.warning(issue)
    valid = int(checks.status.eq("Hợp lệ").sum())
    for column, label, value in zip(st.columns(3), ["Điểm đo", "Chu kỳ hợp lệ", "Chu kỳ có lỗi"], [count, valid, len(checks) - valid]):
        with column:
            st.metric(label, value)
    tabs = st.tabs(["Kết quả kiểm tra", "Cấu trúc cột", "Xem trước 100 dòng"])
    with tabs[0]:
        only_errors = st.checkbox("Chỉ hiện chu kỳ có lỗi")
        shown = checks[checks.status.ne("Hợp lệ")] if only_errors else checks
        st.dataframe(vietnamese_table(shown), hide_index=True, width="stretch")
        csv_download("Tải báo cáo chu kỳ", vietnamese_table(checks), "kiem_tra_chu_ky.csv")
        if not issue and not checks.empty and valid == len(checks):
            st.success("Dữ liệu đầu vào hợp lệ.")
    with tabs[1]:
        st.dataframe(schema, hide_index=True, width="stretch")
        csv_download("Tải báo cáo cột", schema, "kiem_tra_cot.csv")
    with tabs[2]:
        st.dataframe(vietnamese_table(preview), hide_index=True, width="stretch")

