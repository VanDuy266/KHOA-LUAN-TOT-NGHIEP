"""Tổng quan dữ liệu và các chỉ số thực nghiệm."""

import streamlit as st
from app_data import table, metadata, PHASES
from components import heading, section, stat, number
from charts import soh_trend


def render():
    data = table("reports/features.csv")
    dataset = metadata("reports/dataset_summary.json")
    rf = table("reports/metrics_summary.csv").query("model == 'Random Forest'").iloc[0]
    heading(
        "",
        "Phân tích và dự đoán tình trạng sức khỏe pin xe điện bằng các mô hình học máy",
        "",
    )
    left, right = st.columns([1.55, 1], gap="large")
    with left:
        st.markdown(
            '<div class="hero-panel"><span class="status-pill"><i></i> Dữ liệu nghiên cứu</span>'
            "<h2>Phân tích dữ liệu và dự đoán SOH</h2><p>Dữ liệu SDU · 86 tế bào pin lithium-ion · Hai giai đoạn sử dụng.</p>"
            '<div class="hero-tags"><span>86 pin SDU</span><span>12 đặc trưng</span><span>120 giây đầu</span></div></div>',
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            '<div class="author-card"><div class="author-monogram">VD</div>'
            '<div class="eyebrow">Người thực hiện</div><h2>Nguyễn Văn Duy</h2>'
            "<dl><dt>MSSV</dt><dd>2311553949</dd><dt>Chuyên ngành</dt><dd>Khoa Học Dữ Liệu</dd></dl></div>",
            unsafe_allow_html=True,
        )
    st.write("")
    values = [
        (
            "Dòng đo được chọn",
            number(dataset["all_measurement_rows"]),
            "Xả tham chiếu · hai giai đoạn",
        ),
        (
            "Pin thử nghiệm",
            str(data.battery.nunique()),
            "Cell NMC(532)/graphite · 2,4 Ah",
        ),
        ("Chu kỳ xả", number(len(data)), "Mẫu SOH của mô hình"),
        (
            "MAE · Random Forest",
            f"{rf.mae:.3f}",
            "Điểm phần trăm SOH · kiểm thử theo pin",
        ),
    ]
    for index, (column, item) in enumerate(zip(st.columns(4), values)):
        with column:
            stat(*item, accent=index == 3)
    section("01", "SOH theo chu kỳ", "Dung lượng tham chiếu: 2,4 Ah")
    phase = st.selectbox("Giai đoạn", list(PHASES), format_func=PHASES.get)
    data = data[data.phase == phase]
    pins = st.multiselect(
        "Pin trên biểu đồ",
        sorted(data.battery.unique()),
        default=sorted(data.battery.unique())[:4],
        max_selections=6,
    )
    with st.container(border=True):
        st.altair_chart(
            soh_trend(data[data.battery.isin(pins)]), width="stretch", theme=None
        )
    section("02", "Thống kê từng pin")
    shown = (
        data.groupby("battery")
        .agg(
            chu_ky=("cycle", "count"),
            soh_min=("soh_pct", "min"),
            soh_max=("soh_pct", "max"),
        )
        .reset_index()
    )
    shown.columns = ["Mã pin", "Chu kỳ xả", "SOH thấp nhất (%)", "SOH cao nhất (%)"]
    st.dataframe(shown.round(2), hide_index=True, width="stretch")
