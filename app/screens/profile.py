"""Thông tin đề tài, nguồn dữ liệu và hồ sơ thực nghiệm."""
import streamlit as st
from app_data import ROOT, table
from components import heading, section, csv_download
from labels import vietnamese_table


def render():
    heading("THÔNG TIN", "Vincent D", "Phân tích và ước lượng sức khỏe pin lithium-ion")
    left, right = st.columns([1, 1.45], gap="large")
    with left:
        st.markdown('<div class="profile-card"><div class="author-monogram">VD</div>'
                    '<h2>Nguyễn Văn Duy</h2><dl><dt>MSSV</dt><dd>2311553949</dd>'
                    '<dt>Chuyên ngành</dt><dd>Khoa Học Dữ Liệu</dd><dt>Trường</dt><dd>Đại học Nguyễn Tất Thành</dd></dl></div>', unsafe_allow_html=True)
    with right:
        st.subheader("Phân tích và dự đoán tình trạng sức khỏe pin xe điện bằng các mô hình học máy")
        st.latex(r"SOH\;(\%) = \frac{Q_{xả}\;(Ah)}{2\;(Ah)} \times 100")
        st.caption("Mô hình: Random Forest · 11 đặc trưng · cửa sổ xả 120 giây")
    section("01", "Dữ liệu")
    st.dataframe(vietnamese_table(table("reports/data_audit.csv")).round(3), hide_index=True, width="stretch")
    with st.expander("Nguồn và phạm vi"):
        st.markdown("**NASA PCoE — Battery Data Set**, Saha và Goebel (2007). File MATLAB từ bản lưu `psanabriaUC/BatteryDatasetImplementation`, phiên bản trong manifest.\n\nBốn cell thử nghiệm, 636 chu kỳ xả. Không phải dữ liệu xe điện Việt Nam. Đã kiểm tra danh mục NASA và bản lưu; chưa đối chiếu byte với archive S3 của đơn vị phát hành. Kết quả chưa được đánh giá trên pack hoặc xe vận hành thực tế.")
        st.caption("2.089.048 dòng là các thời điểm đo sạc/xả; không phải hai triệu mẫu SOH độc lập.")
    with st.expander("Nhật ký làm sạch"):
        removed = vietnamese_table(table("reports/removed_measurements.csv"))
        st.dataframe(removed, hide_index=True, width="stretch")
        csv_download("Tải nhật ký", removed, "nhat_ky_lam_sach.csv")
    with st.expander("Phương pháp đánh giá"):
        st.write("Giữ riêng từng pin: học trên ba pin còn lại, kiểm thử pin giữ riêng. Tham số cố định. MAE/RMSE tính theo điểm phần trăm SOH; chỉ số tổng hợp là trung bình không trọng số giữa bốn pin.")
        st.write("RF dùng trong ứng dụng được huấn luyện lại bằng cả bốn pin. Mẫu B0005 có sẵn đã tham gia huấn luyện. Kiểm thử 70/30 theo thời gian là bài toán riêng; RF hiện kém baseline SOH cuối đã biết. Chưa đánh giá RUL.")
        st.write("Khoảng giá trị đặc trưng không phải khoảng tin cậy dự đoán. SOH không phải SOC. Giá trị trên 100% được giữ khi dung lượng đo vượt 2 Ah.")
    section("02", "Tài liệu")
    documents = [("Báo cáo Word", "docs/bao-cao-khoa-luan.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                 ("Slide", "docs/slide-bao-ve.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
                 ("Mô tả dữ liệu", "data/README.md", "text/markdown")]
    for column, (label, relative, mime) in zip(st.columns(3), documents):
        with column:
            path = ROOT / relative
            if path.exists(): st.download_button(label, path.read_bytes(), path.name, mime, width="stretch", icon=":material/download:")
    links = st.columns(2)
    with links[0]: st.link_button("Danh mục NASA", "https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/", width="stretch")
    with links[1]: st.link_button("Kho mã nguồn", "https://github.com/VanDuy266/KHOA-LUAN-TOT-NGHIEP", width="stretch")
