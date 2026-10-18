"""Hồ sơ đề tài, nguồn dữ liệu, thuật ngữ và các tệp báo cáo."""
import streamlit as st
from app_data import ROOT, table, metadata
from components import heading, section, note, csv_download
from labels import vietnamese_table


def render():
    heading("HỒ SƠ / 04", "Đề tài, dữ liệu và tài liệu bàn giao.",
            "Thông tin người thực hiện, cách đọc kết quả và các nguồn dùng trong nghiên cứu.")
    left, right = st.columns([1, 1.45], gap="large")
    with left:
        st.markdown('<div class="profile-card"><div class="author-monogram">ND</div><div class="eyebrow">SINH VIÊN THỰC HIỆN</div>'
                    '<h2>Nguyễn Văn Duy</h2><dl><dt>Mã số sinh viên</dt><dd>2311553949</dd>'
                    '<dt>Chuyên ngành</dt><dd>Khoa Học Dữ Liệu</dd><dt>Trường</dt><dd>Đại học Nguyễn Tất Thành</dd></dl></div>', unsafe_allow_html=True)
    with right:
        st.subheader("Phân tích và dự đoán tình trạng sức khỏe pin xe điện bằng các mô hình học máy")
        st.write("Sản phẩm sử dụng Python, pandas, scipy, scikit-learn và Streamlit. Phần mềm phục vụ tra cứu, kiểm tra thực nghiệm và minh họa dự đoán SOH từ đầu chu kỳ xả.")
        st.latex(r"SOH\;(\%) = \frac{Q_{xả}\;(Ah)}{2\;(Ah)} \times 100")
        note("Phạm vi nghiên cứu", "Dữ liệu thuộc cell lithium-ion trong thí nghiệm, không phải bộ pin xe điện Việt Nam. Một số giá trị SOH trên 100% được giữ nguyên khi dung lượng đo vượt danh định 2 Ah.", "soft")
    section("01", "Nguồn dữ liệu và chất lượng", "Nguồn có phiên bản, checksum và nhật ký xử lý; không tạo thêm dòng để tăng số lượng.")
    st.dataframe(vietnamese_table(table("reports/data_audit.csv")).round(3), hide_index=True, use_container_width=True)
    note("2 dòng đã loại", "B0018 có hai bản ghi sạc thiếu điện áp, dòng và nhiệt độ. Các dòng này được loại có nhật ký; không nội suy để bù. Bộ sạch còn 2.089.048 dòng đo.")
    with st.expander("Xem nhật ký loại dòng"):
        removed = vietnamese_table(table("reports/removed_measurements.csv"))
        st.dataframe(removed, hide_index=True, use_container_width=True)
        csv_download("Tải nhật ký tiếng Việt", removed, "nhat_ky_lam_sach.csv")
    st.markdown("- **Nguồn công bố:** NASA PCoE, Battery Data Set, Saha và Goebel (2007).\n- **Nguồn file thực tế:** bản lưu MATLAB tại `psanabriaUC/BatteryDatasetImplementation`, commit trong manifest.\n- Đã đọc trang danh mục NASA và README thí nghiệm. Chưa so sánh byte với archive S3 của đơn vị phát hành.")
    links = st.columns(3)
    with links[0]: st.link_button("Danh mục NASA", "https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/", use_container_width=True)
    with links[1]: st.link_button("Repository dự án", "https://github.com/VanDuy266/KHOA-LUAN-TOT-NGHIEP", use_container_width=True)
    with links[2]: st.link_button("Tải dataset đầy đủ", "https://github.com/VanDuy266/KHOA-LUAN-TOT-NGHIEP/raw/refs/heads/main/delivery/Dataset_Pin_NASA_2tr_dong.zip", use_container_width=True)
    section("02", "Thuật ngữ dùng trong ứng dụng", "Giữ ký hiệu chuyên ngành và giải thích bằng tiếng Việt để dễ đối chiếu báo cáo.")
    for title, body in [
        ("SOH · Sức khỏe pin", "Tỷ lệ dung lượng xả so với dung lượng danh định. Biến đích của nghiên cứu này."),
        ("SOC · Trạng thái sạc", "Lượng điện còn lại tương đối tại một thời điểm. SOH 90% không có nghĩa pin đang còn 90% mức sạc."),
        ("RUL · Tuổi thọ còn lại", "Phần thời gian hoặc số chu kỳ tới ngưỡng kết thúc tuổi thọ. Sản phẩm chưa đánh giá bài toán này."),
        ("Giữ riêng pin để kiểm thử", "Một pin không xuất hiện trong huấn luyện ở vòng tạo ra dự đoán kiểm thử của pin đó.")]:
        with st.expander(title): st.write(body)
    section("03", "Tài liệu để đọc và báo cáo", "Bảng số liệu gốc được lưu trong reports; tên cột tiếng Việt chỉ phục vụ trình bày.")
    documents = [
        ("Báo cáo Word", "docs/bao-cao-khoa-luan.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("Slide bảo vệ", "docs/slide-bao-ve.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        ("Giải thích code", "docs/giai-thich-code.md", "text/markdown"),
        ("Mô tả dataset", "data/README.md", "text/markdown"),
    ]
    for column, (label, relative, mime) in zip(st.columns(4), documents):
        with column:
            path = ROOT / relative
            if path.exists():
                st.download_button(label, path.read_bytes(), path.name, mime, use_container_width=True, icon=":material/download:")
    note("Trước khi nộp chính thức", "Sinh viên cần chạy lại, hiểu và giải thích phương pháp; đối chiếu mẫu trường và yêu cầu giảng viên. Giao diện hoặc số dòng dữ liệu không thay thế chất lượng nghiên cứu.", "soft")
