"""Ứng dụng sinh viên: xem dữ liệu, kết quả và dự đoán một chu kỳ xả."""
import io
import json
import sys
from pathlib import Path
import joblib
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from battery_soh.features import FEATURES, extract_window

st.set_page_config(page_title="Sức khỏe pin lithium-ion", page_icon="🔋", layout="wide")
st.title("🔋 Phân tích và ước lượng sức khỏe pin")
st.caption("Khóa luận khoa học dữ liệu · Nguyễn Văn Duy · Cell lithium-ion · SOH")
st.info("Mô hình nghiên cứu dùng 120 giây đầu chu kỳ xả. Chưa được kiểm chứng trên bộ pin xe điện thực tế.")

required = [ROOT / "reports/features.csv", ROOT / "reports/metrics_summary.csv",
            ROOT / "reports/metrics_by_battery.csv", ROOT / "reports/data_audit.csv",
            ROOT / "reports/predictions.csv", ROOT / "artifacts/random_forest.joblib",
            ROOT / "reports/dataset_summary.json", ROOT / "data/clean/measurements.csv"]
if not all(p.exists() for p in required):
    st.error("Chưa có thực nghiệm. Chạy lần lượt download_data.py, prepare_data.py và run_experiment.py trong thư mục scripts.")
    st.stop()

data = pd.read_csv(ROOT / "reports/features.csv")
metrics = pd.read_csv(ROOT / "reports/metrics_summary.csv")
artifact = joblib.load(ROOT / "artifacts/random_forest.joblib")  # Chỉ đọc mô hình cục bộ do dự án tạo.
dataset = json.loads((ROOT / "reports/dataset_summary.json").read_text(encoding="utf-8"))
overview, results, inference = st.tabs(["Dữ liệu", "Đánh giá mô hình", "Ước lượng từ CSV"])

with overview:
    a, b, c, d = st.columns(4)
    a.metric("Pin trong thực nghiệm", data.battery.nunique())
    b.metric("Chu kỳ hợp lệ", len(data))
    c.metric("Cửa sổ quan sát", "120 giây")
    d.metric("Dòng đo sạch (sạc + xả)", f"{dataset['all_measurement_rows']:,}")
    st.caption("Hơn 2 triệu dòng đo thuộc 4 pin; bảng học máy có một mẫu trên mỗi chu kỳ xả. Không coi mỗi dòng đo là một mẫu SOH độc lập.")
    battery = st.selectbox("Chọn pin", sorted(data.battery.unique()))
    part = data[data.battery == battery].set_index("cycle")
    st.line_chart(part[["soh_pct"]], y_label="SOH (%)", x_label="Chu kỳ xả")
    st.dataframe(pd.read_csv(ROOT / "reports/data_audit.csv"), hide_index=True)
    st.caption("Đã đọc trực tiếp file MATLAB từ bản lưu công khai dẫn nguồn NASA. Trang NASA và mô tả thí nghiệm đã được kiểm tra; chưa đối chiếu byte với kho S3 của đơn vị phát hành. Đây không phải dữ liệu Việt Nam.")
    with st.expander("Quy trình làm sạch"):
        st.write("Loại 2 dòng sạc thiếu tín hiệu trong B0018; không nội suy, không nhân bản. Không cắt SOH về 100%. Các phép đo sạc không được tự gán nhãn SOH tương lai.")
        st.dataframe(pd.read_csv(ROOT / "reports/removed_measurements.csv"), hide_index=True)
    st.download_button("Tải bảng mẫu học máy", (ROOT / "data/clean/cycle_features.csv").read_bytes(), "cycle_features.csv", "text/csv")

with results:
    st.write("Mỗi vòng giữ toàn bộ một pin làm kiểm thử, huấn luyện trên ba pin còn lại. Tham số cố định; không chọn mô hình bằng tập kiểm thử.")
    st.dataframe(metrics, hide_index=True)
    st.caption("MAE/RMSE: điểm phần trăm SOH. Trung bình không trọng số giữa các pin; R² âm nghĩa là kém hơn dự đoán trung bình của pin kiểm thử.")
    st.image(str(ROOT / "reports/held_out_predictions.png"))
    st.dataframe(pd.read_csv(ROOT / "reports/metrics_by_battery.csv"), hide_index=True)
    st.download_button("Tải kết quả theo pin", (ROOT / "reports/metrics_by_battery.csv").read_bytes(), "metrics_by_battery.csv", "text/csv")
    if (ROOT / "reports/ablation_summary.csv").exists():
        with st.expander("Phân tích bổ sung: bỏ đặc trưng và kiểm thử theo thời gian"):
            st.dataframe(pd.read_csv(ROOT / "reports/ablation_summary.csv"), hide_index=True)
            st.dataframe(pd.read_csv(ROOT / "reports/temporal_metrics.csv"), hide_index=True)
            st.caption("Kiểm thử theo thời gian là bài toán khác. RF hiện kém baseline SOH cuối đã biết; chưa thể dùng kết quả này để tuyên bố dự báo RUL.")

with inference:
    st.write("Tải CSV của một chu kỳ xả với các cột: time (giây), terminal_voltage (V), terminal_current (A, âm khi xả), temperature (°C). Không cần nhãn capacity hoặc SOH.")
    st.caption("Cần ít nhất 5 mẫu trong 0–120 giây; bắt đầu ≤20 giây, kết thúc ≥90 giây; ít nhất 3 mẫu dòng xả <−0.1 A trải dài ≥30 giây.")
    example = pd.read_csv(ROOT / "data/clean/measurements.csv")
    example = example[(example.battery == "B0005") & (example.cycle == 1) & (example.time <= 120)][["time", "terminal_voltage", "terminal_current", "temperature"]]
    st.download_button("Tải CSV mẫu của chu kỳ 1 — B0005", example.to_csv(index=False), "example_cycle.csv", "text/csv")
    uploaded = st.file_uploader("CSV một chu kỳ xả (tối đa 5 MB)", type=["csv"])
    cycle = st.number_input("Chỉ số chu kỳ xả", min_value=1, max_value=100000, value=1, step=1)
    use_example = st.checkbox("Dùng CSV mẫu để minh họa")
    if st.button("Ước lượng SOH"):
        try:
            if uploaded is None and not use_example:
                raise ValueError("Hãy tải CSV hoặc chọn dùng mẫu")
            if uploaded is not None and uploaded.size > 5_000_000:
                raise ValueError("File vượt quá 5 MB")
            frame = example if uploaded is None else pd.read_csv(io.BytesIO(uploaded.getvalue()))
            if "cycle" in frame and frame.cycle.nunique(dropna=False) != 1:
                raise ValueError("CSV phải chứa đúng một chu kỳ")
            if "cycle" in frame and not (frame.cycle == cycle).all():
                raise ValueError("Chỉ số chu kỳ nhập không khớp CSV")
            row = pd.DataFrame([extract_window(frame, cycle)])[FEATURES]
            outside = [name for name in FEATURES if row[name].iloc[0] < artifact["training_min"][name]
                       or row[name].iloc[0] > artifact["training_max"][name]]
            if outside:
                st.warning("Đầu vào ngoài phạm vi huấn luyện: " + ", ".join(outside))
            prediction = float(artifact["model"].predict(row)[0])
            st.metric("SOH ước lượng", f"{prediction:.2f}%")
            st.caption("Mô hình demo huấn luyện lại trên cả bốn pin. CSV mẫu là dữ liệu đã học; con số này không đại diện độ chính xác kiểm thử và không phải tư vấn thay pin.")
            st.dataframe(row, hide_index=True)
            output = row.assign(predicted_soh_pct=prediction).to_csv(index=False)
            st.download_button("Tải dự đoán", output, "prediction.csv", "text/csv")
        except (ValueError, TypeError, KeyError, pd.errors.ParserError) as error:
            st.error(str(error))
