"""Dashboard overview: observed data, held-out scores and source scope."""
from html import escape
import streamlit as st
from app_data import ROOT, table, metadata, PHASES
from components import heading, stat, number
from charts import soh_trend


def render():
    data = table("reports/features.csv")
    dataset = metadata("reports/dataset_summary.json")
    metrics = table("reports/metrics_summary.csv")
    names = set(metrics.model)
    score = metrics.query("model == 'Random Forest'").iloc[0]
    score_name = "Random Forest"
    if (ROOT / "reports/hybrid_comparison.csv").exists():
        hybrid = table("reports/hybrid_comparison.csv")
        names.update(hybrid.model)
        score = hybrid.query("model == 'Ridge-RF residual'").iloc[0]
        score_name = "Ridge–RF"
    if (ROOT / "reports/boosting/metadata.json").exists():
        names.update(table("reports/boosting/metrics_summary.csv").model)
    welcome, scope = st.columns([1.65, 1], gap="medium")
    with welcome:
        heading("", "Tổng quan sức khỏe pin", "Tra cứu tín hiệu đo, so sánh mô hình và ước lượng dung lượng còn lại.")
    with scope:
        st.markdown('<div class="dashboard-snapshot"><strong>Phạm vi thực nghiệm</strong><span>SDU · tế bào pin trong phòng thí nghiệm<br>BMS · dữ liệu sạc trên xe BAIC EU500</span></div>', unsafe_allow_html=True)
    values = [
        ("Dòng đo được chọn", number(dataset["all_measurement_rows"]), "Xả tham chiếu · hai giai đoạn", "database"),
        ("Pin thử nghiệm", str(data.battery.nunique()), "Cell NMC(532)/graphite · 2,4 Ah", "battery_full"),
        ("Chu kỳ xả", number(len(data)), "Mẫu SOH của mô hình", "monitoring"),
        (f"MAE · {score_name}", f"{score.mae:.3f}", "Điểm % SOH · trung bình theo pin", "analytics"),
    ]
    for column, (label, value, detail, icon) in zip(st.columns(4, gap="small"), values):
        with column:
            stat(label, value, detail, icon=icon)
    st.write("")
    left, right = st.columns([1.35, 1], gap="medium")
    with left:
        with st.container(border=True):
            st.markdown('<div class="dashboard-panel-title">SOH theo chu kỳ xả</div><div class="dashboard-panel-sub">Dữ liệu đo tham chiếu · xem theo giai đoạn và mã pin</div>', unsafe_allow_html=True)
            filter_phase, filter_pins = st.columns([1, 1.6], gap="small")
            with filter_phase:
                phase = st.selectbox("Giai đoạn", list(PHASES), format_func=PHASES.get)
            selected_data = data[data.phase == phase]
            with filter_pins:
                pins = st.multiselect("Pin trên biểu đồ", sorted(selected_data.battery.unique()), default=sorted(selected_data.battery.unique())[:4], max_selections=6)
            if pins:
                st.altair_chart(soh_trend(selected_data[selected_data.battery.isin(pins)]), width="stretch", theme=None)
            else:
                st.info("Chọn ít nhất một pin để xem đường SOH.")
    with right:
        with st.container(border=True):
            st.markdown('<div class="dashboard-panel-title">Phạm vi dữ liệu và cách đọc kết quả</div><div class="dashboard-panel-sub">Tách rõ dữ liệu cell, dữ liệu trên xe và kết quả kiểm thử</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="dashboard-scope-grid"><div><strong>{data.battery.nunique()} pin</strong><span>SDU · tế bào vật lý</span></div><div><strong>2 giai đoạn</strong><span>Ban đầu · Tái sử dụng</span></div><div><strong>{len(names)} cấu hình</strong><span>Giữ riêng pin kiểm thử</span></div><div><strong>120 giây</strong><span>Cửa sổ tín hiệu đầu xả</span></div><div><strong>12 đặc trưng</strong><span>Mô hình dữ liệu bảng</span></div><div><strong>2,4 Ah</strong><span>Dung lượng danh định SDU</span></div></div>',
                unsafe_allow_html=True,
            )
            st.markdown('<div class="dashboard-callout"><strong>Kết quả đánh giá theo pin</strong><p>MAE/RMSE nhỏ hơn là tốt hơn. Các chu kỳ của cùng một pin được giữ ở cùng phía khi chia tập học và kiểm thử.</p></div>', unsafe_allow_html=True)
            st.caption("BMS có mô hình riêng và nhãn SOH suy ra từ dòng điện/SOC khi sạc. Chưa có phép đo dung lượng độc lập để xác nhận SOH vật lý.")
            with st.expander("Đề tài khóa luận"):
                st.write("Phân tích và dự đoán tình trạng sức khỏe pin xe điện bằng các mô hình học máy")
    st.write("")
    with st.container(border=True):
        st.markdown('<div class="dashboard-panel-title">Thống kê từng pin</div><div class="dashboard-panel-sub">Theo giai đoạn đang chọn · không dùng nhãn SOH để lọc các pin khó</div>', unsafe_allow_html=True)
        shown = selected_data.groupby("battery").agg(chu_ky=("cycle", "count"), soh_min=("soh_pct", "min"), soh_max=("soh_pct", "max")).reset_index()
        shown.columns = ["Mã pin", "Chu kỳ xả", "SOH thấp nhất (%)", "SOH cao nhất (%)"]
        st.dataframe(shown.round(2), hide_index=True, width="stretch")
        st.download_button("Tải thống kê CSV", shown.round(2).to_csv(index=False).encode("utf-8-sig"), file_name=f"thong_ke_pin_{phase}.csv", mime="text/csv", icon=":material/download:")
    st.markdown('<div class="dashboard-footer">Vincent D · Nguyễn Văn Duy · Dashboard nghiên cứu sức khỏe pin · Nguồn và phương pháp trong mục Thông tin.</div>', unsafe_allow_html=True)
