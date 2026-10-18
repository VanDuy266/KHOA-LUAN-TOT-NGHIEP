"""Trang tổng quan: số liệu thật, xu hướng và giới thiệu quy trình."""
import streamlit as st
from app_data import table, metadata
from components import heading, section, stat, number, note
from charts import soh_trend


def render():
    data = table("reports/features.csv")
    dataset = metadata("reports/dataset_summary.json")
    metrics = table("reports/metrics_summary.csv")
    rf = metrics[metrics.model == "Random Forest"].iloc[0]
    heading("KHÓA LUẬN TỐT NGHIỆP / KHOA HỌC DỮ LIỆU", "Sức khỏe pin, nhìn từ dữ liệu.",
            "Tra cứu quá trình suy giảm dung lượng, so sánh mô hình học máy và ước lượng SOH từ tín hiệu đầu chu kỳ xả.")
    left, right = st.columns([1.55, 1], gap="large")
    with left:
        st.markdown('<div class="hero-panel"><span class="status-pill"><i></i> DỮ LIỆU ĐÃ KIỂM TRA</span>'
                    '<h2>Phân tích và dự đoán tình trạng sức khỏe pin xe điện</h2>'
                    '<p>Nghiên cứu trên cell lithium-ion. Mỗi kết quả đều có nguồn dữ liệu, cách đánh giá và phạm vi áp dụng rõ ràng.</p>'
                    '<div class="hero-tags"><span>Python</span><span>scikit-learn</span><span>Streamlit</span></div></div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="author-card"><div class="author-monogram">ND<span>01</span></div>'
                    '<div class="eyebrow">SINH VIÊN THỰC HIỆN</div><h2>Nguyễn Văn Duy</h2>'
                    '<dl><dt>Mã số sinh viên</dt><dd>2311553949</dd><dt>Chuyên ngành</dt><dd>Khoa Học Dữ Liệu</dd></dl></div>', unsafe_allow_html=True)
    st.write("")
    columns = st.columns(4)
    values = [("DÒNG ĐO SẠCH", number(dataset["all_measurement_rows"]), "Gồm phép đo sạc và xả"),
              ("PIN THỬ NGHIỆM", str(data.battery.nunique()), "B0005 · B0006 · B0007 · B0018"),
              ("MẪU SOH", number(len(data)), "Một mẫu cho mỗi chu kỳ xả"),
              ("MAE · RANDOM FOREST", f"{rf.mae:.3f}", "Điểm phần trăm SOH · kiểm thử theo pin")]
    for index, (column, values_one) in enumerate(zip(columns, values)):
        with column:
            stat(*values_one, accent=index == 3)
    section("01", "Quá trình suy giảm SOH", "Di chuột trên đường biểu diễn để xem từng chu kỳ. Các đường thuộc bốn cell thử nghiệm.")
    with st.container(border=True):
        st.altair_chart(soh_trend(data), use_container_width=True, theme=None)
    section("02", "Chọn mục để bắt đầu", "Điều hướng ở thanh bên trái; mỗi mục có dữ liệu và phần giải thích riêng.")
    for column, title, body in zip(st.columns(3),
        ["01 / Tra cứu pin", "02 / Đánh giá mô hình", "03 / Dự đoán SOH"],
        ["Chọn pin, lọc chu kỳ, xem điện áp, dòng điện và nhiệt độ thực đo.",
         "Đọc MAE, RMSE, R² và đối chiếu dự đoán với pin được giữ riêng để kiểm thử.",
         "Dùng mẫu có sẵn hoặc tải CSV một chu kỳ xả để ước lượng SOH."]):
        with column:
            note(title, body)
    note("Hiểu đúng số liệu", "2.089.048 dòng đo không phải hai triệu mẫu nhãn độc lập. Nghiên cứu có 636 chu kỳ xả và bốn pin; chưa kiểm chứng trên bộ pin xe điện thực tế hoặc dữ liệu Việt Nam.", "soft")
