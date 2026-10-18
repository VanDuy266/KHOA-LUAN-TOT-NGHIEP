"""Tổng quan dữ liệu và các chỉ số thực nghiệm."""
import streamlit as st
from app_data import table, metadata
from components import heading, section, stat, number
from charts import soh_trend


def render():
    data = table("reports/features.csv")
    dataset = metadata("reports/dataset_summary.json")
    rf = table("reports/metrics_summary.csv").query("model == 'Random Forest'").iloc[0]
    heading("VINCENT D / PHÂN TÍCH PIN", "Tổng quan sức khỏe pin", "Dữ liệu lithium-ion · Tra cứu chu kỳ · Ước lượng SOH")
    left, right = st.columns([1.55, 1], gap="large")
    with left:
        st.markdown('<div class="hero-panel"><span class="status-pill"><i></i> BỘ DỮ LIỆU NGHIÊN CỨU</span>'
                    '<h2>Phân tích sức khỏe pin lithium-ion</h2><p>Theo dõi dung lượng theo chu kỳ và đối chiếu kết quả của các mô hình học máy.</p>'
                    '<div class="hero-tags"><span>4 pin</span><span>636 chu kỳ xả</span><span>120 giây đầu</span></div></div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="author-card"><div class="author-monogram">VD</div>'
                    '<div class="eyebrow">NGƯỜI THỰC HIỆN</div><h2>Nguyễn Văn Duy</h2>'
                    '<dl><dt>MSSV</dt><dd>2311553949</dd><dt>Chuyên ngành</dt><dd>Khoa Học Dữ Liệu</dd></dl></div>', unsafe_allow_html=True)
    st.write("")
    values = [("DÒNG ĐO SẠCH", number(dataset["all_measurement_rows"]), "Sạc và xả"),
              ("PIN THỬ NGHIỆM", str(data.battery.nunique()), "B0005 · B0006 · B0007 · B0018"),
              ("CHU KỲ XẢ", number(len(data)), "Mẫu SOH của mô hình"),
              ("MAE · RANDOM FOREST", f"{rf.mae:.3f}", "Điểm phần trăm SOH · kiểm thử theo pin")]
    for index, (column, item) in enumerate(zip(st.columns(4), values)):
        with column: stat(*item, accent=index == 3)
    section("01", "SOH theo chu kỳ", "Dung lượng tham chiếu: 2 Ah")
    with st.container(border=True): st.altair_chart(soh_trend(data), width="stretch", theme=None)
    section("02", "Thống kê từng pin")
    shown = data.groupby("battery").agg(chu_ky=("cycle", "count"), soh_min=("soh_pct", "min"), soh_max=("soh_pct", "max")).reset_index()
    shown.columns = ["Mã pin", "Chu kỳ xả", "SOH thấp nhất (%)", "SOH cao nhất (%)"]
    st.dataframe(shown.round(2), hide_index=True, width="stretch")
