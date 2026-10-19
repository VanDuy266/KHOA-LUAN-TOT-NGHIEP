"""Truy xuất nguồn và kết quả kiểm tra chất lượng."""

import streamlit as st
from app_data import table, metadata
from components import heading, section, stat, number, csv_download
from labels import vietnamese_table


def render():
    summary = metadata("reports/dataset_summary.json")
    heading(
        "DỮ LIỆU / CHẤT LƯỢNG",
        "Nguồn và chất lượng dữ liệu",
        "SDU 2025 · DOI 10.5281/zenodo.14859405 · CC BY 4.0",
    )
    for col, item in zip(
        st.columns(4),
        [
            (
                "ĐIỂM ĐO",
                number(summary["all_measurement_rows"]),
                "172 file · hai giai đoạn",
            ),
            ("MẪU CHU KỲ", number(summary["feature_rows"]), "86 pin vật lý"),
            ("THIẾU TÍN HIỆU BẮT BUỘC", "0", "Thời gian, điện áp, dòng điện, nhiệt độ"),
            (
                "ĐIỂM CẦN XEM XÉT",
                str(summary["suspected_points"]),
                "Không có điểm nào trong 120 giây đầu",
            ),
        ],
    ):
        with col:
            stat(*item)
    section("01", "Từ nguồn đến bảng mô hình")
    stages = [
        ("145.112.317", "Dòng đo nguồn", "Hai gói ZIP gốc được đối chiếu MD5."),
        (
            "30.929.675",
            "Dòng xả tham chiếu",
            "20.823 chu kỳ có điều kiện xả tương đồng.",
        ),
        (
            "10.505.065",
            "Dòng được giữ",
            "Giữ toàn bộ cửa sổ đầu, điểm cuối; lấy thưa phần giữa.",
        ),
        ("20.823 × 12", "Bảng đặc trưng", "Một mẫu mỗi chu kỳ, giai đoạn và pin."),
    ]
    for col, (value, title, text) in zip(st.columns(4), stages):
        with col:
            with st.container(border=True):
                st.subheader(value)
                st.write(title)
                st.caption(text)
    st.write(
        "Giữ nguyên giá trị các dòng được chọn từ nguồn. Không tạo thêm dữ liệu, không nội suy và không tự sửa các điểm nghi vấn. Bộ chọn không chứa toàn bộ các trạng thái sạc, nghỉ hoặc mọi chế độ xả của nguồn."
    )
    section("02", "Các kiểm tra đã thực hiện")
    st.dataframe(
        vietnamese_table(table("reports/data_audit.csv")),
        hide_index=True,
        width="stretch",
    )
    st.write(
        "Có 23 bước thời gian đi lùi trong thứ tự ghi nguồn. Bản dùng xử lý được sắp theo thời gian trong từng chu kỳ; file nguồn được giữ nguyên. Các đặc trưng đã được tính lại để đối chiếu với bảng nhãn."
    )
    with st.expander("Điểm nghi vấn còn giữ lại", expanded=False):
        points = table("reports/suspected_measurements.csv")
        st.caption(
            "Đánh dấu theo biến thiên tín hiệu; chưa đủ căn cứ kết luận là lỗi cảm biến. Không tự xóa hoặc sửa."
        )
        st.dataframe(vietnamese_table(points), hide_index=True, width="stretch")
        csv_download("Tải danh sách điểm nghi vấn", points, "diem_can_kiem_tra.csv")
    section("03", "Đặc trưng và nhãn")
    from battery_soh.features import FEATURES
    from labels import COLUMNS
    import pandas as pd

    st.dataframe(
        pd.DataFrame(
            {"Tên trong mã": FEATURES, "Ý nghĩa": [COLUMNS.get(x, x) for x in FEATURES]}
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "SOH = dung lượng xả toàn chu kỳ / 2,4 Ah × 100. Không ép SOH về 100%; không dùng dung lượng, SOH hay thời lượng toàn chu kỳ làm đặc trưng."
    )
