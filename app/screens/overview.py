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
        "Tổng quan sức khỏe pin",
        "Dữ liệu SDU · Phân tích chu kỳ xả và đánh giá SOH",
    )
    left, right = st.columns([1.55, 1], gap="large")
    with left:
        st.markdown(
            '<div class="hero-panel"><span class="status-pill"><i></i> Dữ liệu nghiên cứu</span>'
            "<h2>Phân tích và dự đoán tình trạng sức khỏe pin xe điện bằng các mô hình học máy</h2><p>Tra cứu tín hiệu đo, so sánh mô hình và ước lượng dung lượng còn lại.</p>"
            '<div class="hero-tags"><span>SDU · NMC/graphite</span><span>12 đặc trưng</span><span>Cửa sổ 120 giây</span></div></div>',
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            '<div class="author-card"><div class="eyebrow">Phạm vi phân tích</div>'
            '<h2>Hai giai đoạn sử dụng</h2>'
            '<dl><dt>Loại pin</dt><dd>NMC(532)/graphite</dd><dt>Dung lượng</dt><dd>2,4 Ah</dd>'
            '<dt>Giai đoạn</dt><dd>Ban đầu · Tái sử dụng</dd><dt>Chỉ số</dt><dd>SOH theo dung lượng</dd></dl></div>',
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
    filter_phase, filter_pins = st.columns([1, 2], gap="large")
    with filter_phase:
        phase = st.selectbox("Giai đoạn", list(PHASES), format_func=PHASES.get)
    data = data[data.phase == phase]
    with filter_pins:
        pins = st.multiselect(
            "Pin trên biểu đồ",
            sorted(data.battery.unique()),
            default=sorted(data.battery.unique())[:4],
            max_selections=6,
        )
    with st.container(border=True):
        if pins:
            st.altair_chart(
                soh_trend(data[data.battery.isin(pins)]), width="stretch", theme=None
            )
        else:
            st.info("Chọn ít nhất một pin để xem đường SOH.")
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
    st.download_button(
        "Tải thống kê CSV",
        shown.round(2).to_csv(index=False).encode("utf-8-sig"),
        file_name=f"thong_ke_pin_{phase}.csv",
        mime="text/csv",
        icon=":material/download:",
    )
