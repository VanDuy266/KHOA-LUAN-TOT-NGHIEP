"""Lịch sử dự đoán chỉ tồn tại trong phiên Streamlit hiện tại."""
import pandas as pd
import streamlit as st
from components import heading, csv_download
from labels import vietnamese_table
from result_report import html_report, current_time


def render():
    heading("LỊCH SỬ", "Kết quả dự đoán trong phiên", "Các kết quả được lưu tạm trong phiên hiện tại, tối đa 500 chu kỳ.")
    history = st.session_state.get("prediction_history", [])
    if not history:
        st.info("Chưa có lịch sử dự đoán.")
        return
    data = pd.DataFrame(history).drop(columns="request_id")
    a, b, c = st.columns(3)
    with a: st.metric("Chu kỳ đã xử lý", len(data))
    with b: st.metric("Thành công", int(data.status.eq("Thành công").sum()))
    with c: st.metric("Không hợp lệ", int(data.status.ne("Thành công").sum()))
    status = st.selectbox("Trạng thái", ["Tất cả", "Thành công", "Không hợp lệ"])
    shown = data if status == "Tất cả" else data[data.status == status]
    st.dataframe(vietnamese_table(shown).round(3), hide_index=True, width="stretch")
    left, middle, right = st.columns(3)
    with left: csv_download("Tải lịch sử CSV", vietnamese_table(shown), "vincent_d_lich_su.csv")
    with middle:
        st.download_button("Tải phiếu tổng hợp", html_report(shown, current_time(), "Lịch sử phiên").encode("utf-8"),
                           "vincent_d_tong_hop.html", "text/html", width="stretch")
    with right:
        if st.button("Xóa lịch sử phiên", type="secondary", width="stretch"):
            st.session_state.pop("prediction_history", None)
            st.session_state.pop("forecast_result", None)
            st.rerun()
