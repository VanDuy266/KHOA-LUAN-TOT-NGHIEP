"""Đọc kết quả kiểm thử đã lưu; không huấn luyện hoặc chọn lại mô hình trên test."""

import streamlit as st
from app_data import ROOT, table, PHASES, evaluation_results
from charts import model_comparison, held_out, residuals
from components import heading, section, stat, note, csv_download
from labels import MODEL_NAMES, vietnamese_table


def render():
    metrics, by_battery, predictions, phases, timings = evaluation_results()
    heading(
        "THỰC NGHIỆM / 02",
        "Đánh giá mô hình",
        f"Kiểm thử giữ riêng pin · 5 vòng theo nhóm pin · {len(metrics)} cấu hình",
    )
    with st.expander("Các mô hình trong thực nghiệm"):
        st.write(
            "Ridge: hồi quy tuyến tính điều chuẩn, tính nhanh và dễ phân tích hệ số. Random Forest: nhiều cây học quan hệ phi tuyến. LightGBM: tăng cường cây theo phần sai số còn lại. GRU: học chuỗi điện áp, dòng điện và nhiệt độ theo thứ tự thời gian."
        )
        st.caption(
            "GRU dùng 25 vị trí trong 120 giây và hai biến ngữ cảnh; các mô hình bảng dùng 12 thống kê. Mốc trung bình SOH là đối chứng. Khác biệt điểm số gồm cả ảnh hưởng biểu diễn và cấu hình, chưa phải kết luận về mọi cấu hình của thuật toán."
        )
    if "Ridge-RF residual" in metrics.model.values:
        note("Ridge–RF · Phương án khóa luận",
             "Ridge ước lượng xu hướng nền; Random Forest hiệu chỉnh phần dư. "
             "Cùng 12 đặc trưng, cùng 5 nhóm pin kiểm thử với các mô hình đối chứng. "
             "Chọn mô hình bên dưới để xem chỉ số, dự đoán và thời gian huấn luyện.", kind="soft")
        with st.expander("Cách kết hợp và đối chiếu với Random Forest"):
            st.latex(r"\widehat{SOH} = Ridge(X) + RF_{phần\ dư}(X)")
            st.caption("Phương án kết hợp thuật toán có sẵn được kiểm chứng trong khóa luận; không khẳng định là thuật toán mới hoặc tốt hơn trên mọi bộ dữ liệu.")
            st.dataframe(vietnamese_table(table("reports/hybrid_paired_comparison.csv")).round(3), hide_index=True, width="stretch")
            csv_download("Tải đối chiếu theo pin", table("reports/hybrid_paired_comparison.csv"), "so_sanh_cap_ridge_rf.csv")
    if "CatBoost" in metrics.model.values:
        with st.expander("CatBoost / XGBoost · Cách chọn tham số và nguồn phương pháp"):
            st.write("Hai thư viện chính thức, cùng 12 đặc trưng và 5 nhóm pin SDU. Mỗi vòng thử 3 cấu hình trên nhóm pin validation bên trong train, chọn số cây rồi học lại train đầy đủ trước khi dự đoán pin test.")
            st.caption("Mô hình mới có ngân sách chọn tham số, đối chứng cũ dùng cấu hình cố định. Chênh lệch gồm cả ảnh hưởng thuật toán và ngân sách tìm kiếm; không khẳng định mô hình mới tốt hơn trong mọi điều kiện. Thời gian chọn tham số được ghi riêng, ngoài thời gian refit. Các mẫu trong ứng dụng đã tham gia refit.")
            st.link_button("CatBoost · NeurIPS 2018", "https://proceedings.neurips.cc/paper/2018/hash/14491b756b3a51daac41c24863285549-Abstract.html")
            st.link_button("XGBoost · KDD 2016", "https://arxiv.org/abs/1603.02754")
    names = metrics.model.tolist()
    model = st.selectbox(
        "Mô hình cần xem",
        names,
        index=0,
        key="evaluation_model",
        format_func=lambda name: MODEL_NAMES[name],
    )
    score = metrics[metrics.model == model].iloc[0]
    for column, label, value, detail in zip(
        st.columns(3),
        [
            "SAI SỐ TUYỆT ĐỐI · MAE",
            "CĂN SAI SỐ BÌNH PHƯƠNG · RMSE",
            "HỆ SỐ XÁC ĐỊNH · R²",
        ],
        [f"{score.mae:.3f}", f"{score.rmse:.3f}", f"{score.r2:.3f}"],
        [
            "Điểm phần trăm SOH · nhỏ hơn là tốt hơn",
            "Điểm phần trăm SOH · nhạy với lỗi lớn",
            "Trung bình theo pin · có thể mang giá trị âm",
        ],
    ):
        with column:
            stat(label, value, detail)
    section("01", "So sánh cấu hình", "Trung bình không trọng số giữa 86 pin")
    left, right = st.columns([1.3, 1], gap="large")
    with left:
        with st.container(border=True):
            metric = st.selectbox(
                "Chỉ số trên biểu đồ",
                ["mae", "rmse", "r2"],
                format_func=lambda key: {
                    "mae": "MAE — sai số tuyệt đối",
                    "rmse": "RMSE — sai số bình phương",
                    "r2": "R² — hệ số xác định",
                }[key],
            )
            st.altair_chart(
                model_comparison(metrics, metric), width="stretch", theme=None
            )
    with right:
        st.dataframe(
            vietnamese_table(metrics).round(3),
            hide_index=True,
            width="stretch",
            column_config={
                "Mô hình": st.column_config.TextColumn("Mô hình", width="medium"),
                "MAE (điểm % SOH)": st.column_config.NumberColumn(
                    "MAE",
                    width="small",
                    format="%.3f",
                    help="Sai số tuyệt đối, đơn vị điểm phần trăm SOH",
                ),
                "RMSE (điểm % SOH)": st.column_config.NumberColumn(
                    "RMSE",
                    width="small",
                    format="%.3f",
                    help="Căn sai số bình phương, đơn vị điểm phần trăm SOH",
                ),
                "R²": st.column_config.NumberColumn("R²", width="small", format="%.3f"),
            },
        )
        csv_download(
            "Tải bảng so sánh tiếng Việt",
            vietnamese_table(metrics),
            "so_sanh_mo_hinh.csv",
        )
        st.caption("MAE/RMSE: điểm phần trăm SOH · Tím: Ridge–RF · Cam: Random Forest")
    section("02", "Thực tế và dự đoán", "Dự đoán từ pin giữ riêng trong kiểm thử")
    phase = st.selectbox("Giai đoạn kiểm thử", list(PHASES), format_func=PHASES.get)
    battery = st.selectbox("Pin kiểm thử", sorted(predictions.battery.unique()))
    part = predictions[
        (predictions.model == model)
        & (predictions.battery == battery)
        & (predictions.phase == phase)
    ]
    with st.container(border=True):
        st.altair_chart(held_out(part), width="stretch", theme=None)
    st.dataframe(
        vietnamese_table(by_battery[by_battery.model == model]).round(3),
        hide_index=True,
        width="stretch",
    )
    with st.expander("Chỉ số theo giai đoạn và thời gian huấn luyện"):
        st.caption(
            "Chỉ số giai đoạn tính gộp các chu kỳ; bảng chính lấy trung bình theo pin. Thời gian đo trên môi trường thực nghiệm, có thể khác máy cá nhân."
        )
        st.dataframe(
            vietnamese_table(phases[phases.model == model]).round(3),
            hide_index=True,
            width="stretch",
        )
        st.dataframe(
            vietnamese_table(timings[timings.model == model]).round(3).astype(object).where(timings[timings.model == model].notna().to_numpy(), "Chưa ghi nhận"),
            hide_index=True,
            width="stretch",
        )
    st.caption("Thời gian dự đoán chưa được lưu cho GRU và Ridge–RF; không quy đổi thành 0 giây.")
    section(
        "03",
        "Sai số ở từng chu kỳ",
        "Sai số dương: dự đoán cao hơn thực tế. Sai số âm: dự đoán thấp hơn thực tế.",
    )
    with st.container(border=True):
        st.altair_chart(
            residuals(predictions[predictions.model == model]),
            width="stretch",
            theme=None,
        )
    csv_download(
        "Tải dự đoán kiểm thử của mô hình",
        vietnamese_table(predictions[predictions.model == model]),
        "du_doan_kiem_thu.csv",
    )
    if (ROOT / "reports/ablation_summary.csv").exists():
        section("04", "Các kiểm tra bổ sung", "Đặc trưng và phân hoạch thời gian")
        ablation, temporal = st.tabs(["Bỏ nhóm đặc trưng", "Kiểm thử theo thời gian"])
        with ablation:
            st.dataframe(
                vietnamese_table(table("reports/ablation_summary.csv")).round(3),
                hide_index=True,
                width="stretch",
            )
            st.caption("Random Forest · tham số cố định")
        with temporal:
            st.dataframe(
                vietnamese_table(table("reports/temporal_metrics.csv")).round(3),
                hide_index=True,
                width="stretch",
            )
            st.caption(
                "Học từ 70% chu kỳ đầu của từng pin trong từng giai đoạn; kiểm thử 30% cuối. Mô hình học trên dữ liệu quá khứ gộp của 86 pin. Kết quả này tách riêng kiểm thử pin mới."
            )
