# SDU — bộ dữ liệu xả tham chiếu

10.505.065 dòng đo, 20.823 chu kỳ, 86 pin vật lý, hai giai đoạn và 172 CSV gzip.

## Quy tắc chọn

Từ 30.929.675 dòng xả tham chiếu, giữ mọi điểm trong 120 giây đầu và điểm cuối mỗi chu kỳ. Phần còn lại được sắp theo thời gian, giữ một trong ba điểm, bắt đầu từ điểm đầu của phần này. Số 10.505.065 là kết quả đếm thực tế, không phải ngân sách dòng đặt trước. Không thêm điểm giả, không nhân bản, không sửa số đo; các dòng CSV chọn giữ nguyên văn từ nguồn. Đây là tập con, không phải toàn bộ nguồn tác giả 145.112.317 dòng.

## Chất lượng

Đã đọc đủ 172 file, đối chiếu SHA-256 và tính lại đặc trưng/nhãn. Không phát hiện thiếu tín hiệu bắt buộc, trùng khóa thời gian hoặc giá trị ngoài ngưỡng kiểm tra. Có 26 điểm nghi vấn được giữ, không điểm nào trong 120 giây đầu. Có 23 bước thời gian đi lùi trong thứ tự nguồn; bản sao xử lý được sắp trong chu kỳ. Xem verification/summary.json và KET_QUA_KIEM_TRA.md. Không tuyên bố dữ liệu hoàn toàn không có nhiễu.

## Sử dụng

Giữ nguyên .csv.gz trong source_rows/Primary_use_phase và source_rows/Second_life_phase. Python đọc trực tiếp gzip. training_table.csv có 20.823 mẫu; chỉ dùng feature_columns trong dataset_summary.json. Dung lượng/SOH lấy từ chu kỳ đầy đủ, không tích phân lại bản đã lấy thưa. Hai giai đoạn của cùng pin phải ở cùng phía khi chia tập.

Nguồn: Wang, Gao và Tian (2025), https://doi.org/10.5281/zenodo.14859405, CC BY 4.0. Pin Lishen LR1865SZ NMC(532)/graphite, 2,4 Ah, phòng thí nghiệm. Chi tiết tại NGUON_DU_LIEU.md.

Sản phẩm Vincent D có dữ liệu Parquet và mô hình: https://github.com/VanDuy266/KHOA-LUAN-TOT-NGHIEP/archive/refs/heads/san-pham-sdu.zip
