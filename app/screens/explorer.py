"""Tra cứu theo pin và chu kỳ; các đồ thị sử dụng phép đo thật."""
import pandas as pd
import streamlit as st
from app_data import table
from charts import soh_trend, signal
from components import heading, section, stat, csv_download, number
from labels import vietnamese_table


def render():
    features = table("reports/features.csv")
    heading("TRA CỨU DỮ LIỆU / 01", "Tra cứu dữ liệu pin",
            "SOH và tín hiệu đo theo chu kỳ xả")
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
    section("01", "So sánh sức khỏe pin", "Bốn cell lithium-ion · dung lượng tham chiếu 2 Ah")
    with st.container(border=True): st.altair_chart(soh_trend(subset), width="stretch", theme=None)
    section("02", "Mở một chu kỳ xả", "Điện áp · dòng điện · nhiệt độ")
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
            with st.container(border=True): st.altair_chart(signal(detail, name, label, color), width="stretch", theme=None)
    with st.expander("Bảng phép đo và tải dữ liệu chu kỳ"):
        st.dataframe(vietnamese_table(detail[["time", "terminal_voltage", "terminal_current", "temperature", "capacity"]]),
                     hide_index=True, width="stretch")
        csv_download("Tải CSV chu kỳ đang xem", detail, f"{battery}_chu_ky_{cycle}.csv")
    render_comparison(features, measurements)
    section("04", "Bảng SOH theo bộ lọc")
    shown = vietnamese_table(subset[["battery", "cycle", "soh_pct"]])
    st.dataframe(shown, hide_index=True, width="stretch", height=280)
    left, right = st.columns(2)
    with left: csv_download("Tải bảng SOH tiếng Việt", shown, "bang_soh.csv")
    with right: csv_download("Tải đặc trưng gốc theo bộ lọc", subset, "cycle_features_filtered.csv")


def render_comparison(features, measurements):
    from charts import compare_signal
    section("03", "So sánh hai chu kỳ")
    chosen = []
    for index, column in enumerate(st.columns(2)):
        letter = "A" if index == 0 else "B"
        with column:
            pin = st.selectbox("Pin " + letter, sorted(features.battery.unique()), index=index, key="compare_pin_" + letter)
            options = features[features.battery == pin].cycle.astype(int).tolist()
            cycle = st.select_slider("Chu kỳ " + letter, options=options, value=options[0], key="compare_cycle_" + letter)
            chosen.append((pin, cycle, letter))
    scope = st.selectbox("Cửa sổ so sánh", ["120 giây đầu", "Toàn bộ chu kỳ"])
    parts, summary = [], []
    for pin, cycle, letter in chosen:
        part = measurements[(measurements.battery == pin) & (measurements.cycle == cycle)].copy()
        if scope == "120 giây đầu": part = part[part.time <= 120]
        part["comparison"] = f"{letter} · {pin} · {cycle}"
        parts.append(part)
        value = features[(features.battery == pin) & (features.cycle == cycle)].iloc[0]
        summary.append({"Mẫu": letter, "Mã pin": pin, "Chu kỳ": cycle, "SOH thực đo (%)": value.soh_pct,
                        "Dung lượng (Ah)": value.soh_pct / 100 * 2})
    combined = pd.concat(parts, ignore_index=True)
    st.dataframe(pd.DataFrame(summary).round(3), hide_index=True, width="stretch")
    for column, name, label in zip(st.columns(3), ["terminal_voltage", "terminal_current", "temperature"],
                                  ["Điện áp (V)", "Dòng điện (A)", "Nhiệt độ (°C)"]):
        with column: st.altair_chart(compare_signal(combined, name, label), width="stretch", theme=None)
    csv_download("Tải bảng so sánh A/B", pd.DataFrame(summary), "vincent_d_so_sanh_chu_ky.csv")
