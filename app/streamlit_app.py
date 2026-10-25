"""Điểm vào ứng dụng. Mỗi màn hình nằm riêng trong app/screens để dễ sửa."""

import sys
import json
from html import escape
from pathlib import Path
import streamlit as st

APP = Path(__file__).resolve().parent
ROOT = APP.parent
# Cho phép chạy từ thư mục bất kỳ bằng streamlit run app/streamlit_app.py.
sys.path.insert(0, str(APP))
sys.path.insert(0, str(ROOT / "src"))

from components import logo_image, brand_wordmark

from screens import (
    overview,
    explorer,
    evaluation,
    forecast,
    profile,
    history,
    quality,
    anomalies,
    demo,
    input_check,
    bms,
)

st.set_page_config(
    page_title="Vincent D · Sức khỏe pin",
    page_icon=str(APP / "assets" / "vincent-d-logo-avatar.png"),
    layout="wide",
    initial_sidebar_state="auto",
)
st.markdown(
    "<style>" + (APP / "styles.css").read_text(encoding="utf-8") + "</style>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        f'<div class="brand"><div class="brand-mark brand-logo">{logo_image()}</div><div><div class="brand-name">{brand_wordmark()}</div>'
        '<div class="brand-sub">Phân tích sức khỏe pin</div></div></div><div class="sidebar-heading">KHÔNG GIAN LÀM VIỆC</div>',
        unsafe_allow_html=True,
    )
    page = st.radio(
        "Điều hướng",
        [
            "Tổng quan", "Tra cứu pin", "Kiểm tra file đầu vào", "Dự đoán SOH",
            "Lịch sử dự đoán", "Xu hướng bất thường", "Đánh giá mô hình",
            "Demo pin giữ riêng", "BMS trên xe", "Chất lượng dữ liệu", "Thông tin",
        ],
        label_visibility="collapsed",
        key="navigation",
        format_func=lambda name: f":material/{dict(zip(
            ["Tổng quan", "Tra cứu pin", "Kiểm tra file đầu vào", "Dự đoán SOH",
             "Lịch sử dự đoán", "Xu hướng bất thường", "Đánh giá mô hình",
             "Demo pin giữ riêng", "BMS trên xe", "Chất lượng dữ liệu", "Thông tin"],
            ["dashboard", "battery_full", "fact_check", "online_prediction",
             "history", "monitoring", "analytics", "play_circle", "science",
             "verified", "info"]
        ))[name]}:  {name}",
    )
    st.markdown(
        f'<div class="sidebar-person"><div class="avatar-orbit avatar-logo">{logo_image()}</div><div><strong>Nguyễn Văn Duy</strong><small>MSSV 2311553949<br>Khoa Học Dữ Liệu</small></div></div>',
        unsafe_allow_html=True,
    )

    st.toggle("Giao diện tối", key="dashboard_dark")

# Theme variables are presentation only; native controls retain their behavior.
dark = st.session_state.get("dashboard_dark", False)
colors = ("#111b29", "#1b2838", "#e5edf5", "#9aabc0", "#2c3b4d", "#211f32", "#75d69e", "#ff7a84", "#34304d") if dark else ("#f4f7fb", "#ffffff", "#243b5c", "#788499", "#e0e6ef", "#f1f2f7", "#157347", "#b4232f", "#e2e0ee")
keys = ("bg", "surface", "text", "muted", "line", "sidebar", "green", "red", "active")
st.markdown("<style>:root{" + ";".join(f"--dash-{key}:{value}" for key, value in zip(keys, colors)) + "}</style>", unsafe_allow_html=True)
st.markdown(
    f'<div class="dashboard-topbar"><div><span class="top-brand">Vincent D</span><span class="top-separator">/</span><span class="top-page">{escape(page)}</span></div><span class="top-context">Phân tích sức khỏe pin</span></div>',
    unsafe_allow_html=True,
)

required = [
    "reports/features.csv",
    "reports/metrics_summary.csv",
    "reports/metrics_by_battery.csv",
    "reports/data_audit.csv",
    "reports/predictions.csv",
    "reports/dataset_summary.json",
    "reports/removed_measurements.csv",
    "artifacts/random_forest.joblib",
    "data/clean/sample_measurements.csv",
]
missing = [name for name in required if not (ROOT / name).exists()]
if missing:
    st.error("Dữ liệu hệ thống chưa sẵn sàng. Vui lòng liên hệ người quản lý ứng dụng.")
    with st.expander("Các file còn thiếu"):
        st.write(missing)
    st.stop()

dataset = json.loads((ROOT / "reports/dataset_summary.json").read_text())
if dataset.get("dataset") != "SDU":
    st.error("Dữ liệu không khớp phiên bản SDU của ứng dụng.")
    st.stop()

screens = {
    "BMS trên xe": bms.render,
    "Xu hướng bất thường": anomalies.render,
    "Kiểm tra file đầu vào": input_check.render,
    "Demo pin giữ riêng": demo.render,
    "Chất lượng dữ liệu": quality.render,
    "Tổng quan": overview.render,
    "Tra cứu pin": explorer.render,
    "Đánh giá mô hình": evaluation.render,
    "Dự đoán SOH": forecast.render,
    "Thông tin": profile.render,
    "Lịch sử dự đoán": history.render,
}
screens[page]()
