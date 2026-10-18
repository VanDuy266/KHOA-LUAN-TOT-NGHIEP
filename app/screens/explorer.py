"""Tra cứu theo pin và chu kỳ; các đồ thị sử dụng phép đo thật."""
import streamlit as st
from app_data import table
from charts import soh_trend, signal
from components import heading, section, stat, csv_download, number
from labels import vietnamese_table


def render():
    features = table("reports/features.csv")
    heading("TRA CỨU DỮ LIỆU / 01", "Từng pin. Từng chu kỳ.",
            "Lọc dữ liệu để xem xu hướng SOH và mở chi tiết tín hiệu đo của một chu kỳ xả.")
    with st.container(border=True):
        left, right = st.columns([1, 1.4], gap="large")
        with left:
            selected = st.multiselect("Pin cần so sánh", sorted(features.battery.unique()), default=sorted(features.battery.unique()))
        with right:
            cycle_range = st.slider("Khoảng chu kỳ xả", int(features.cycle.min()), int(features.cycle.max()),
                                    (int(features.cycle.min()), int(features.cycle.max())))
    subset = features[features.battery.isin(selected) & features.cycle.between(*cycle_range)]
    if subset.empty:
        st.info("Chưa có dữ liệu trong bộ lọc này. Hãy chọn ít nhất một pin hoặc mở rộng khoảng chu kỳ.")
        return
    cols = st.columns(3)
    with cols[0]: stat("PIN ĐANG XEM", str(subset.battery.nunique()), "Trong bộ lọc hiện tại")
    with cols[1]: stat("CHU KỲ HIỂN THỊ", number(len(subset)), "Mỗi điểm là một chu kỳ xả")
    with cols[2]: stat("KHOẢNG SOH", f"{subset.soh_pct.min():.1f}–{subset.soh_pct.max():.1f}%", "Tính theo dung lượng danh định 2 Ah", True)
    section("01", "So sánh sức khỏe pin", "Chú giải màu giúp phân biệt pin. Số chu kỳ của mỗi pin có thể khác nhau.")
    with st.container(border=True): st.altair_chart(soh_trend(subset), use_container_width=True, theme=None)
    section("02", "Mở một chu kỳ xả", "Xem toàn bộ tín hiệu đo hoặc riêng cửa sổ 120 giây được mô hình sử dụng.")
    controls = st.columns([1, 1.5, 1])
    with controls[0]:
        battery = st.selectbox("Pin xem chi tiết", sorted(subset.battery.unique()))
    choices = subset[subset.battery == battery].cycle.astype(int).tolist()
    with controls[1]:
        cycle = st.select_slider("Chu kỳ xem chi tiết", options=choices, value=choices[0])
    with controls[2]:
        window = st.selectbox("Phạm vi tín hiệu", ["Toàn bộ chu kỳ", "120 giây đầu"])
    measurements = table("data/clean/measurements.csv")
    detail = measurements[(measurements.battery == battery) & (measurements.cycle == cycle)].copy()
    if window == "120 giây đầu": detail = detail[detail.time <= 120]
    actual = features[(features.battery == battery) & (features.cycle == cycle)].soh_pct.iloc[0]
    st.caption(f"{battery} · chu kỳ {cycle} · SOH thực đo {actual:.2f}% · {len(detail)} điểm đo đang hiển thị")
    for column, name, label, color in zip(st.columns(3),
        ["terminal_voltage", "terminal_current", "temperature"],
        ["Điện áp (V)", "Dòng điện (A)", "Nhiệt độ (°C)"],
        ["#087f70", "#6576a8", "#eb8c5e"]):
        with column:
            with st.container(border=True): st.altair_chart(signal(detail, name, label, color), use_container_width=True, theme=None)
    with st.expander("Bảng phép đo và tải dữ liệu chu kỳ"):
        st.dataframe(vietnamese_table(detail[["time", "terminal_voltage", "terminal_current", "temperature", "capacity"]]),
                     hide_index=True, use_container_width=True)
        csv_download("Tải CSV chu kỳ đang xem", detail, f"{battery}_chu_ky_{cycle}.csv")
    section("03", "Bảng SOH theo bộ lọc", "Bảng xuất tiếng Việt phục vụ đọc báo cáo; bảng đặc trưng gốc giữ nguyên tên cột để chạy mô hình.")
    shown = vietnamese_table(subset[["battery", "cycle", "soh_pct"]])
    st.dataframe(shown, hide_index=True, use_container_width=True, height=280)
    left, right = st.columns(2)
    with left: csv_download("Tải bảng SOH tiếng Việt", shown, "bang_soh.csv")
    with right: csv_download("Tải đặc trưng gốc theo bộ lọc", subset, "cycle_features_filtered.csv")
