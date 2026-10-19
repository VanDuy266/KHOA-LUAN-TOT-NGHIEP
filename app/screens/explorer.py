"""Tra cứu tín hiệu theo pin, giai đoạn và chu kỳ."""

import pandas as pd
import streamlit as st
from app_data import table, cycle_measurements, PHASES
from components import heading, section, stat, csv_download, number
from charts import soh_trend, signal, compare_signal
from labels import vietnamese_table


def render():
    data = table("reports/features.csv")
    heading(
        "DỮ LIỆU / SDU 2025",
        "Tra cứu và so sánh pin",
        "Cell NMC(532)/graphite · 2,4 Ah · 86 pin",
    )
    a, b = st.columns([1, 2])
    with a:
        phase = st.selectbox("Giai đoạn", list(PHASES), format_func=PHASES.get)
    phase_data = data[data.phase == phase]
    with b:
        pins = st.multiselect(
            "Pin cần so sánh",
            sorted(phase_data.battery.unique()),
            default=sorted(phase_data.battery.unique())[:3],
            max_selections=6,
        )
    limit = st.slider(
        "Khoảng chu kỳ",
        int(phase_data.cycle.min()),
        int(phase_data.cycle.max()),
        (int(phase_data.cycle.min()), int(phase_data.cycle.max())),
    )
    selected = phase_data[
        phase_data.battery.isin(pins) & phase_data.cycle.between(*limit)
    ]
    if selected.empty:
        st.info("Chưa có dữ liệu trong bộ lọc này.")
        return
    for col, label, value, note in zip(
        st.columns(3),
        ["PIN ĐANG XEM", "CHU KỲ", "KHOẢNG SOH"],
        [
            str(len(pins)),
            number(len(selected)),
            f"{selected.soh_pct.min():.1f}–{selected.soh_pct.max():.1f}%",
        ],
        ["Trong bộ lọc", "Chu kỳ tham chiếu", "Dung lượng danh định 2,4 Ah"],
    ):
        with col:
            stat(label, value, note)
    st.altair_chart(soh_trend(selected), width="stretch", theme=None)
    st.caption(
        "Biểu đồ giới hạn 400 điểm mỗi pin; file xuất giữ đầy đủ các chu kỳ theo bộ lọc."
    )
    section("01", "Tín hiệu chu kỳ")
    a, b, c = st.columns(3)
    with a:
        pin = st.selectbox("Pin xem chi tiết", sorted(selected.battery.unique()))
    choices = selected[selected.battery == pin].cycle.astype(int).tolist()
    with b:
        cycle = st.select_slider(
            "Chu kỳ xem chi tiết", options=choices, value=choices[0]
        )
    with c:
        scope = st.selectbox("Phạm vi tín hiệu", ["120 giây đầu", "Toàn bộ đoạn xả"])
    raw = cycle_measurements(pin, cycle, phase)
    detail = raw[raw.time <= 120] if scope == "120 giây đầu" else raw
    truth = selected[(selected.battery == pin) & (selected.cycle == cycle)].iloc[0]
    st.caption(
        f"{PHASES[phase]} · {pin} · Chu kỳ {cycle} · SOH {truth.soh_pct:.2f}% · Dung lượng {truth.capacity_ah:.4f} Ah · {len(detail):,} điểm đo"
    )
    for col, key, label in zip(
        st.columns(3),
        ["terminal_voltage", "terminal_current", "temperature"],
        ["Điện áp (V)", "Dòng điện (A)", "Nhiệt độ (°C)"],
    ):
        with col:
            st.altair_chart(signal(detail, key, label), width="stretch", theme=None)
    st.caption(
        "Sau 120 giây: điểm đo đã lấy thưa. Dữ liệu nguồn và nhãn đầy đủ được lưu để đối chiếu."
    )
    with st.expander("Bảng phép đo"):
        st.dataframe(vietnamese_table(detail), hide_index=True, width="stretch")
        csv_download("Tải CSV chu kỳ", detail, f"{phase}_{pin}_{cycle}.csv")
    section("02", "So sánh hai chu kỳ")
    parts = []
    rows = []
    for index, col in enumerate(st.columns(2)):
        letter = "A" if index == 0 else "B"
        with col:
            stage = st.selectbox(
                "Giai đoạn " + letter,
                list(PHASES),
                format_func=PHASES.get,
                key="stage_" + letter,
            )
            battery = st.selectbox(
                "Pin " + letter,
                sorted(data.battery.unique()),
                index=index,
                key="compare_pin_" + letter,
            )
            options = (
                data[(data.battery == battery) & (data.phase == stage)]
                .cycle.astype(int)
                .tolist()
            )
            chosen = st.select_slider(
                "Chu kỳ " + letter,
                options=options,
                value=options[0],
                key="compare_cycle_" + letter,
            )
            part = (
                cycle_measurements(battery, chosen, stage).query("time <= 120").copy()
            )
            part["comparison"] = f"{letter} · {battery} · {PHASES[stage]} · {chosen}"
            parts.append(part)
            actual = data[
                (data.battery == battery)
                & (data.phase == stage)
                & (data.cycle == chosen)
            ].iloc[0]
            rows.append(
                {
                    "Mẫu": letter,
                    "Mã pin": battery,
                    "Giai đoạn": PHASES[stage],
                    "Chu kỳ": chosen,
                    "SOH (%)": actual.soh_pct,
                    "Dung lượng (Ah)": actual.capacity_ah,
                }
            )
    st.dataframe(pd.DataFrame(rows).round(3), hide_index=True, width="stretch")
    for col, key, label in zip(
        st.columns(3),
        ["terminal_voltage", "terminal_current", "temperature"],
        ["Điện áp (V)", "Dòng điện (A)", "Nhiệt độ (°C)"],
    ):
        with col:
            st.altair_chart(
                compare_signal(pd.concat(parts), key, label),
                width="stretch",
                theme=None,
            )
    section("03", "Bảng chu kỳ")
    st.dataframe(
        vietnamese_table(
            selected[["battery", "phase", "cycle", "capacity_ah", "soh_pct"]]
        ).round(4),
        hide_index=True,
        width="stretch",
        height=280,
    )
    csv_download("Tải bảng chu kỳ theo bộ lọc", selected, "sdu_chu_ky.csv")
