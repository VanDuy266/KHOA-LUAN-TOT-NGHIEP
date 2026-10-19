"""Nguồn dữ liệu, phạm vi nghiên cứu và tài liệu thực nghiệm."""

import streamlit as st
from app_data import ROOT, table, metadata
from components import heading, section, csv_download
from labels import vietnamese_table


def render():
    heading("THÔNG TIN", "Vincent D", "Phân tích và ước lượng sức khỏe pin lithium-ion")
    left, right = st.columns([1, 1.45], gap="large")
    with left:
        st.markdown(
            '<div class="profile-card"><div class="author-monogram">VD</div><h2>Nguyễn Văn Duy</h2><dl><dt>MSSV</dt><dd>2311553949</dd><dt>Chuyên ngành</dt><dd>Khoa Học Dữ Liệu</dd></dl></div>',
            unsafe_allow_html=True,
        )
    with right:
        st.subheader(
            "Phân tích và dự đoán tình trạng sức khỏe pin xe điện bằng các mô hình học máy"
        )
        st.latex(r"SOH\;(\%) = \frac{Q_{xả}\;(Ah)}{2.4\;(Ah)} \times 100")
        st.caption("SDU · NMC(532)/graphite · 12 đặc trưng · 120 giây đầu xả")
    section("01", "Nguồn dữ liệu")
    st.write(
        "Shuquan Wang, Feng Gao và Hao Tian, Đại học Sơn Đông (Trung Quốc). Bộ dữ liệu công bố ngày 12/02/2025 trên Zenodo, DOI: 10.5281/zenodo.14859405; giấy phép CC BY 4.0."
    )
    st.write(
        "Nghiên cứu liên quan: Deep sorting of reused batteries for enabling long-term consistency grouping with unknown prior conditions, Cell Reports Physical Science, DOI: 10.1016/j.xcrp.2025.102657."
    )
    st.write(
        "86 tế bào pin Lishen LR1865SZ, NMC(532)/graphite, dung lượng danh định 2,4 Ah. Hai giai đoạn sử dụng ban đầu và tái sử dụng thuộc cùng 86 pin; không phải 172 pin độc lập."
    )
    st.caption(
        "Đây là dữ liệu thí nghiệm tế bào pin, chưa phải dữ liệu bộ pin xe vận hành tại Việt Nam."
    )
    with st.expander("Thiết kế thực nghiệm"):
        st.write(
            "GroupKFold 5 vòng theo mã pin vật lý. Hai giai đoạn của một pin luôn nằm cùng phía huấn luyện hoặc kiểm thử. Chỉ số chính là trung bình không trọng số giữa 86 pin. Tham số được cố định, không tối ưu trên tập kiểm thử."
        )
        st.write(
            "Kiểm thử thời gian dùng 70% chu kỳ đầu trong từng pin và giai đoạn để học, 30% cuối để kiểm tra. Kết quả được báo cáo riêng với kiểm thử pin mới."
        )
        st.write(
            "Mô hình dùng trên ứng dụng được học lại từ toàn bộ bảng đặc trưng. Dữ liệu mẫu đã tham gia huấn luyện, không dùng để chứng minh khả năng dự đoán pin mới."
        )
    with st.expander("Phạm vi và giới hạn"):
        st.write(
            "Đầu vào gồm số chu kỳ, giai đoạn, điện áp, dòng điện và nhiệt độ trong 120 giây đầu xả. Dung lượng cuối chu kỳ chỉ tạo nhãn, không đưa vào đặc trưng."
        )
        st.write(
            "SOH khác mức sạc SOC. Kết quả chưa phải chứng nhận an toàn, chưa dự báo tuổi thọ còn lại RUL và chưa được kiểm chứng trên bộ pin xe điện thực tế."
        )
        st.write(
            "Bộ 10 triệu dòng giữ đủ các chu kỳ đã chọn, nhưng giảm mật độ điểm đo sau cửa sổ đầu xả. Những chu kỳ sạc, nghỉ hoặc điều kiện xả khác không thuộc bộ chọn này."
        )
    section("02", "Tài liệu nghiên cứu")
    for column, (label, relative, mime) in zip(
        st.columns(3),
        [
            (
                "Báo cáo Word",
                "docs/bao-cao-khoa-luan.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            (
                "Slide",
                "docs/slide-bao-ve.pptx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ),
            ("Nguồn dữ liệu", "data/README.md", "text/markdown"),
        ],
    ):
        with column:
            path = ROOT / relative
            if path.exists():
                st.download_button(
                    label, path.read_bytes(), path.name, mime, width="stretch"
                )
    for col, label, url in zip(
        st.columns(3),
        ["Dữ liệu SDU 2025", "Bài báo gốc", "Kho mã nguồn"],
        [
            "https://zenodo.org/records/14859405",
            "https://doi.org/10.1016/j.xcrp.2025.102657",
            "https://github.com/VanDuy266/KHOA-LUAN-TOT-NGHIEP",
        ],
    ):
        with col:
            st.link_button(label, url, width="stretch")
