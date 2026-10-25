"""Tra cứu lịch sử trong phiên và kho kết quả cục bộ."""

import pandas as pd
import sqlite3
import streamlit as st
from components import heading, csv_download
from app_data import PUBLIC_DEMO
from labels import vietnamese_table
from result_report import html_report, current_time


def render():
    heading(
        "LỊCH SỬ",
        "Lịch sử dự đoán",
        "Tra cứu, lọc và xuất kết quả theo pin, nguồn dữ liệu và thời gian.",
    )
    scope = st.radio("Nguồn lịch sử", ["Phiên hiện tại"] if PUBLIC_DEMO else ["Phiên hiện tại", "Kho trên máy"], horizontal=True, key="history_scope")
    if scope == "Kho trên máy" and not PUBLIC_DEMO:
        from history_store import load_results

        st.caption("Kho chung trên máy chủ · Lưu kết quả và tên nguồn.")
        try:
            history = load_results()
        except (OSError, sqlite3.Error) as error:
            st.error(f"Không đọc được kho kết quả: {error}")
            return
    else:
        history = st.session_state.get("prediction_history", [])
    if not history:
        st.info("Chưa có lịch sử dự đoán.")
        return
    data = pd.DataFrame(history).drop(columns="request_id")
    a, b, c = st.columns(3)
    with a:
        st.metric("Chu kỳ đã xử lý", len(data))
    with b:
        st.metric("Thành công", int(data.status.eq("Thành công").sum()))
    with c:
        st.metric("Không hợp lệ", int(data.status.ne("Thành công").sum()))
    status = st.selectbox("Trạng thái", ["Tất cả", "Thành công", "Không hợp lệ"])
    shown = data if status == "Tất cả" else data[data.status == status]
    left_filter, right_filter = st.columns(2)
    with left_filter:
        query = st.text_input("Tìm mã pin hoặc tên nguồn", placeholder="Ví dụ: SDU_01")
    with right_filter:
        phases = st.multiselect("Giai đoạn", [0, 1], format_func=lambda value: "Sử dụng ban đầu" if value == 0 else "Tái sử dụng")
    if query.strip():
        shown = shown[shown.battery.astype(str).str.contains(query.strip(), case=False, regex=False) | shown.source.astype(str).str.contains(query.strip(), case=False, regex=False)]
    if phases:
        shown = shown[shown.phase_code.isin(phases)]
    dates = pd.to_datetime(data.created_at, format="%d/%m/%Y %H:%M:%S", errors="coerce").dt.date
    valid_dates = dates.dropna()
    if not valid_dates.empty:
        period = st.date_input("Khoảng ngày", value=(valid_dates.min(), valid_dates.max()))
        if len(period) == 2:
            shown = shown[dates.loc[shown.index].between(*period)]
    order = st.selectbox("Sắp xếp", ["Mới nhất", "Cũ nhất", "SOH tăng dần", "SOH giảm dần"])
    if order in ["Mới nhất", "Cũ nhất"]:
        shown = shown.assign(_time=pd.to_datetime(shown.created_at, format="%d/%m/%Y %H:%M:%S", errors="coerce")).sort_values("_time", ascending=order == "Cũ nhất", kind="stable").drop(columns="_time")
    else:
        shown = shown.sort_values("predicted_soh_pct", ascending=order == "SOH tăng dần", na_position="last", kind="stable")
    size_column, page_column = st.columns(2)
    with size_column:
        size = st.selectbox("Số dòng mỗi trang", [25, 50, 100], index=1)
    pages = max(1, (len(shown) + size - 1) // size)
    with page_column:
        page = st.selectbox("Trang kết quả", list(range(1, pages + 1)))
    st.caption(f"{len(shown)} / {len(data)} kết quả · Trang {page}/{pages} · Xuất toàn bộ kết quả đã lọc")
    st.dataframe(vietnamese_table(shown.iloc[(page - 1) * size:page * size]).round(3), hide_index=True, width="stretch")
    left, middle, right = st.columns(3)
    with left:
        csv_download(
            "Tải lịch sử CSV", vietnamese_table(shown), "vincent_d_lich_su.csv"
        )
    with middle:
        st.download_button(
            "Tải phiếu tổng hợp",
            html_report(shown, current_time(), scope).encode("utf-8"),
            "vincent_d_tong_hop.html",
            "text/html",
            width="stretch",
        )
    with right:
        if scope == "Phiên hiện tại" and st.button("Xóa lịch sử phiên", type="secondary", width="stretch"):
            st.session_state.pop("prediction_history", None)
            st.session_state.pop("forecast_result", None)
            st.rerun()
