# SDU — bộ chọn 10 triệu dòng

10.000.000 dòng đo xả, 20.823 chu kỳ, 86 pin vật lý, 172 CSV gzip qua hai giai đoạn. Giữ toàn bộ 120 giây đầu và điểm cuối chu kỳ; lấy thưa phần sau. Các dòng được chọn giữ nguyên giá trị và văn bản từ nguồn. Đây là tập con của bộ tác giả, không phải nguyên bộ 145 triệu dòng.

Nguồn: Wang, Gao và Tian (2025), DOI 10.5281/zenodo.14859405, CC BY 4.0. Chi tiết tại NGUON_DU_LIEU.md và KET_QUA_KIEM_TRA.md. Có 25 điểm nghi vấn còn giữ, không nằm trong cửa sổ mô hình; không tự sửa hoặc xóa.

## Tải và sử dụng

Tải cả nhánh bằng Code → Download ZIP. Chỉ giải nén ZIP bên ngoài, giữ nguyên các file .csv.gz trong source_rows/Primary_use_phase và source_rows/Second_life_phase. Python đọc trực tiếp gzip.

Bảng training_table.csv và cycle_features.csv giữ nhãn/đặc trưng từ chu kỳ đầy đủ. Khóa gồm pin, giai đoạn và chu kỳ; chỉ dùng danh sách feature_columns trong dataset_summary.json làm đầu vào. Không tính lại dung lượng bằng đường đã lấy thưa.

## Sản phẩm sử dụng dữ liệu

Vincent D đã tích hợp bộ chọn này, có Ridge, Random Forest, LightGBM, GRU và mốc trung bình, kiểm thử theo pin. Bản sản phẩm có sẵn Parquet và mô hình tại nhánh san-pham-sdu:
https://github.com/VanDuy266/KHOA-LUAN-TOT-NGHIEP/archive/refs/heads/san-pham-sdu.zip

Bộ dữ liệu nguồn này nộp riêng cùng hồ sơ nguồn, nhật ký chọn và verification/. Script build_10m.py là bước tạo bộ chọn, cần các thư mục selection và quality_review của quy trình nguồn; không cần chạy script đó để đọc bộ đã tải.
