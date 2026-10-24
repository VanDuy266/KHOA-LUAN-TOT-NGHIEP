"""Tra cứu cờ xu hướng trên chuỗi SOH tham chiếu đã quan sát."""

import altair as alt
import streamlit as st
from app_data import table, PHASES, ROOT
from components import heading, section, csv_download


def render():
    heading("", "Xu hướng SOH bất thường", "Giám sát chuỗi SOH tham chiếu theo chu kỳ")
    if not (ROOT / "reports/anomaly_predictions.csv").exists():
        st.info("Chưa có kết quả phân tích xu hướng.")
        return
    data = table("reports/anomaly_predictions.csv")
    a, b = st.columns(2)
    with a:
        phase = st.selectbox("Giai đoạn", list(PHASES), format_func=PHASES.get)
    subset = data[data.phase == phase]
    with b:
        battery = st.selectbox("Mã pin", sorted(subset.battery.unique()))
    part = subset[subset.battery == battery].sort_values("cycle")
    eligible = int(part.eligible.sum())
    flagged = int(part.flag.sum())
    for col, label, value in zip(
        st.columns(3),
        ["Chu kỳ có lịch sử đủ", "Chu kỳ cần xem xét", "Tỷ lệ gắn cờ"],
        [eligible, flagged, f"{100*flagged/eligible:.1f}%" if eligible else "—"],
    ):
        with col:
            st.metric(label, value)
    st.caption(
        "Tỷ lệ gắn cờ không phải độ chính xác phát hiện lỗi. Các cờ là gợi ý kiểm tra, không phải kết luận pin hỏng hoặc nguy hiểm."
    )
    base = alt.Chart(part).encode(x=alt.X("cycle:Q", title="Chu kỳ xả"))
    observed = base.mark_line(color="#087f70").encode(
        y=alt.Y("soh_pct:Q", title="SOH (%)", scale=alt.Scale(zero=False))
    )
    expected = base.mark_line(color="#6576a8", strokeDash=[5, 4]).encode(
        y="expected_soh:Q"
    )
    flags = (
        alt.Chart(part[part.flag])
        .mark_point(color="#bc4c37", size=70, filled=True)
        .encode(
            x="cycle:Q",
            y="soh_pct:Q",
            tooltip=[
                alt.Tooltip("cycle:Q", title="Chu kỳ"),
                alt.Tooltip("soh_pct:Q", title="SOH (%)"),
                alt.Tooltip("reason:N", title="Lý do"),
            ],
        )
    )
    st.altair_chart(
        (observed + expected + flags)
        .properties(height=350)
        .configure_axis(labelFont="Arial", titleFont="Arial"),
        width="stretch",
    )
    st.caption(
        "Xanh: SOH đã đo · Nét đứt: dự kiến từ lịch sử trước đó · Đỏ: chu kỳ được gắn cờ. Không nối qua hai giai đoạn."
    )
    section("01", "Các chu kỳ cần xem xét")
    only_flags = st.checkbox("Chỉ hiện chu kỳ được gắn cờ", value=True)
    shown = part[part.flag] if only_flags else part
    columns = [
        "cycle",
        "soh_pct",
        "expected_soh",
        "innovation_pp",
        "robust_z",
        "iforest_score",
        "iforest_threshold",
        "reason",
    ]
    display = shown[columns].rename(
        columns={
            "cycle": "Chu kỳ",
            "soh_pct": "SOH (%)",
            "expected_soh": "SOH dự kiến (%)",
            "innovation_pp": "Độ lệch (điểm % SOH)",
            "robust_z": "Độ lệch chuẩn hóa",
            "iforest_score": "Điểm Isolation Forest",
            "iforest_threshold": "Ngưỡng từ tập học",
            "reason": "Nhận xét",
        }
    )
    st.dataframe(display.round(4), hide_index=True, width="stretch")
    csv_download(
        "Tải kết quả của pin", part, "xu_huong_" + battery + "_" + phase + ".csv"
    )
    with st.expander("Phương pháp và giới hạn"):
        st.write(
            "Xu hướng nền dùng trung vị tốc độ biến thiên của tối đa 8 khoảng quan sát trước đó, cần ít nhất 5 khoảng. Quy tắc đánh dấu độ lệch chuẩn hóa trên 4,5 và sai lệch SOH ít nhất 1 điểm phần trăm. Khoảng cách số chu kỳ được đưa vào phép tính."
        )
        st.write(
            "Isolation Forest học diễn biến ít gặp. Phân hoạch 5 vòng giữ riêng pin, ngưỡng là phân vị 99% điểm của các pin huấn luyện, không chọn theo pin kiểm thử. Thống kê nền của mỗi thời điểm chỉ lấy từ lịch sử trước đó của cùng pin và giai đoạn."
        )
        st.caption(
            "Cờ xu hướng theo chu kỳ khác các điểm nghi vấn tín hiệu trong trang Chất lượng dữ liệu."
        )
        st.write(
            "Dữ liệu chưa có nhãn lỗi xác nhận nên chưa báo cáo precision, recall hoặc tỷ lệ phát hiện lỗi thực tế. Điểm ít gặp có thể do điều kiện đo, phục hồi dung lượng hoặc nhiễu; không tự xóa dữ liệu được gắn cờ."
        )
        st.write(
            "Đầu vào ở đây là SOH tham chiếu sau phép đo dung lượng, tách khỏi mô hình dự đoán từ 120 giây đầu xả. Chưa kiểm chứng trên dữ liệu BMS hoặc xe thực tế, chưa phải hệ thống cảnh báo trực tuyến."
        )
