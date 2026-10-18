"""Đọc kết quả kiểm thử đã lưu; không huấn luyện hoặc chọn lại mô hình trên test."""
import streamlit as st
from app_data import ROOT, table
from charts import model_comparison, held_out, residuals
from components import heading, section, stat, note, csv_download
from labels import MODEL_NAMES, vietnamese_table


def render():
    metrics = table("reports/metrics_summary.csv")
    by_battery = table("reports/metrics_by_battery.csv")
    predictions = table("reports/predictions.csv")
    heading("THỰC NGHIỆM / 02", "Đánh giá mô hình",
            "Kiểm thử giữ riêng pin · 4 vòng · 5 cấu hình")
    names = metrics.model.tolist()
    model = st.selectbox("Mô hình cần xem", names, index=names.index("Random Forest"), format_func=lambda name: MODEL_NAMES[name])
    score = metrics[metrics.model == model].iloc[0]
    for column, label, value, detail in zip(st.columns(3),
        ["SAI SỐ TUYỆT ĐỐI · MAE", "CĂN SAI SỐ BÌNH PHƯƠNG · RMSE", "HỆ SỐ XÁC ĐỊNH · R²"],
        [f"{score.mae:.3f}", f"{score.rmse:.3f}", f"{score.r2:.3f}"],
        ["Điểm phần trăm SOH · nhỏ hơn là tốt hơn", "Điểm phần trăm SOH · nhạy với lỗi lớn", "Trung bình theo pin · có thể mang giá trị âm"]):
        with column: stat(label, value, detail)
    section("01", "So sánh cấu hình", "Trung bình không trọng số giữa bốn pin")
    left, right = st.columns([1.3, 1], gap="large")
    with left:
        with st.container(border=True):
            metric = st.selectbox("Chỉ số trên biểu đồ", ["mae", "rmse", "r2"], format_func=lambda key: {"mae": "MAE — sai số tuyệt đối", "rmse": "RMSE — sai số bình phương", "r2": "R² — hệ số xác định"}[key])
            st.altair_chart(model_comparison(metrics, metric), width="stretch", theme=None)
    with right:
        st.dataframe(vietnamese_table(metrics).round(3), hide_index=True, width="stretch",
            column_config={
                "Mô hình": st.column_config.TextColumn("Mô hình", width="medium"),
                "MAE (điểm % SOH)": st.column_config.NumberColumn("MAE", width="small", format="%.3f", help="Sai số tuyệt đối, đơn vị điểm phần trăm SOH"),
                "RMSE (điểm % SOH)": st.column_config.NumberColumn("RMSE", width="small", format="%.3f", help="Căn sai số bình phương, đơn vị điểm phần trăm SOH"),
                "R²": st.column_config.NumberColumn("R²", width="small", format="%.3f"),
            })
        csv_download("Tải bảng so sánh tiếng Việt", vietnamese_table(metrics), "so_sanh_mo_hinh.csv")
        st.caption("MAE/RMSE: điểm phần trăm SOH · Màu cam: Random Forest")
    section("02", "Thực tế và dự đoán", "Dự đoán từ pin giữ riêng trong kiểm thử")
    battery = st.selectbox("Pin kiểm thử", sorted(predictions.battery.unique()))
    part = predictions[(predictions.model == model) & (predictions.battery == battery)]
    with st.container(border=True): st.altair_chart(held_out(part), width="stretch", theme=None)
    st.dataframe(vietnamese_table(by_battery[by_battery.model == model]).round(3), hide_index=True, width="stretch")
    section("03", "Sai số ở từng chu kỳ", "Sai số dương: dự đoán cao hơn thực tế. Sai số âm: dự đoán thấp hơn thực tế.")
    with st.container(border=True): st.altair_chart(residuals(predictions[predictions.model == model]), width="stretch", theme=None)
    csv_download("Tải dự đoán kiểm thử của mô hình", vietnamese_table(predictions[predictions.model == model]), "du_doan_kiem_thu.csv")
    if (ROOT / "reports/ablation_summary.csv").exists():
        section("04", "Các kiểm tra bổ sung", "Đặc trưng và phân hoạch thời gian")
        ablation, temporal = st.tabs(["Bỏ nhóm đặc trưng", "Kiểm thử theo thời gian"])
        with ablation:
            st.dataframe(vietnamese_table(table("reports/ablation_summary.csv")).round(3), hide_index=True, width="stretch")
            st.caption("Random Forest · tham số cố định")
        with temporal:
            st.dataframe(vietnamese_table(table("reports/temporal_metrics.csv")).round(3), hide_index=True, width="stretch")
            st.caption("Phân hoạch 70/30 theo thời gian: RF có MAE cao hơn baseline SOH cuối đã biết ở cả bốn pin.")
