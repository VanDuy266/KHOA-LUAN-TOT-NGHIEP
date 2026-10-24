"""Demo độc lập với mô hình sản phẩm học trên toàn bộ pin."""

import hashlib
from pathlib import Path
import streamlit as st
from app_data import ROOT, _model, table, PHASES
from battery_soh.features import FEATURES
from components import heading, csv_download
from explanation import render_explanation


@st.cache_data(show_spinner=False, max_entries=2)
def source_hash(path, modified):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render():
    heading("", "Kiểm thử trên pin giữ riêng", "Random Forest · SDU_01 không tham gia huấn luyện ở cả hai giai đoạn")
    path = ROOT / "artifacts/random_forest_demo.joblib"
    if not path.exists():
        st.info("Chưa có mô hình demo. Chạy: python scripts/build_demo_model.py")
        return
    artifact = _model(str(path), path.stat().st_mtime_ns)
    source = ROOT / "reports/features.csv"
    if artifact["data_sha256"] != source_hash(str(source), source.stat().st_mtime_ns):
        st.error("Dữ liệu đã thay đổi. Cần tạo lại mô hình demo.")
        return
    pin = artifact["held_out_battery"]
    if pin in artifact["batteries"]:
        st.error("Pin demo bị trùng với tập huấn luyện.")
        return
    data = table("reports/features.csv")
    held = data[data.battery == pin].copy()
    st.caption(
        f"Huấn luyện: {len(artifact['batteries'])} pin · {artifact['n_train']:,} chu kỳ. "
        f"Kiểm thử: {pin} · {len(held):,} chu kỳ."
    )
    with st.expander("Dữ liệu kiểm thử"):
        st.write("Đầu vào: đặc trưng của 120 giây đầu xả. SOH thực tế dùng để tính sai số. Kết quả kiểm thử 5 vòng ở mục Đánh giá mô hình.")
    phase = st.selectbox("Giai đoạn demo", list(PHASES), format_func=PHASES.get)
    selected = held[held.phase == phase].sort_values("cycle").copy()
    if selected.empty:
        st.info("Pin không có dữ liệu trong giai đoạn này.")
        return
    selected["predicted_soh_pct"] = artifact["model"].predict(selected[FEATURES])
    cycle = st.selectbox("Chu kỳ demo", selected.cycle.tolist())
    row = selected[selected.cycle == cycle].iloc[[0]]
    actual = float(row.soh_pct.iloc[0])
    prediction = float(row.predicted_soh_pct.iloc[0])
    for column, label, value in zip(st.columns(3),
        ["SOH dự đoán", "SOH thực tế", "Sai số tuyệt đối"],
        [f"{prediction:.2f}%", f"{actual:.2f}%", f"{abs(prediction - actual):.3f} điểm %"]):
        with column:
            st.metric(label, value)
    baseline = float(data[data.battery != pin].soh_pct.mean())
    st.caption(
        f"Toàn giai đoạn đã chọn · MAE mô hình: {(selected.predicted_soh_pct - selected.soh_pct).abs().mean():.3f} "
        f"điểm % · MAE mốc trung bình tập học: {(selected.soh_pct - baseline).abs().mean():.3f} điểm %."
    )
    st.line_chart(selected.set_index("cycle")[["soh_pct", "predicted_soh_pct"]].rename(
        columns={"soh_pct": "SOH thực tế (%)", "predicted_soh_pct": "SOH dự đoán (%)"}))
    render_explanation(artifact, row[FEATURES])
    export = selected[["battery", "phase", "cycle", "soh_pct", "predicted_soh_pct"]].copy()
    export["absolute_error"] = (export.predicted_soh_pct - export.soh_pct).abs()
    csv_download("Tải kết quả pin giữ riêng", export, "kiem_thu_SDU_01.csv")
