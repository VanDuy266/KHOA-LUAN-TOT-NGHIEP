# SDU 2025 — bộ nhỏ cho máy cá nhân

- 2,956,738 dòng đo xả, 2,064 chu kỳ, 86 pin vật lý.
- Tối đa 12 chu kỳ nguyên vẹn trên mỗi pin/giai đoạn. Chọn trải đều theo thứ tự chu kỳ, gồm đầu và cuối; không chọn theo giá trị SOH hoặc điểm mô hình.
- Giảm 90.4% số dòng so với bộ 30.929.675 dòng. Giảm số mẫu có thể ảnh hưởng sai số và độ ổn định; cần đánh giá mô hình lại, không dùng lại chỉ số của bộ lớn.
- Từng dòng đo, tên cột, mã pin, số chu kỳ và thứ tự nguồn được giữ nguyên văn. Không sửa số đo, điền thiếu, nội suy hay nhân bản. Bộ gốc và bộ 30,9 triệu dòng vẫn giữ riêng.

## File

`source_rows/`: CSV nguồn đã chọn dòng, nén gzip, chia theo giai đoạn và file nguồn. Đây là tập con do dự án tạo, không phải gói gốc tác giả phát hành.

`training_table.csv`: bảng nhỏ để huấn luyện. Đầu vào phải lấy đúng danh sách feature_columns trong dataset_summary.json; đích soh_pct. Battery dùng chia nhóm, không làm đặc trưng.

`cycle_features.csv`: đặc trưng, nhãn và thông tin truy nguồn. Các giá trị này đã được tính từ bộ lựa chọn lớn, không phải cột có sẵn trong CSV nguồn.

`source_preservation_audit.csv`: kiểm đếm và SHA-256 nội dung CSV sau giải nén, được đối chiếu với các byte chọn từ nguồn.

Nguồn: https://zenodo.org/records/14859405 — DOI 10.5281/zenodo.14859405, công bố 12/02/2025, CC BY 4.0. Wang, Gao và Tian: Deep sorting of reused batteries for enabling long-term consistency grouping with unknown prior conditions. Pin NMC(532)/graphite Lishen LR1865SZ, danh định 2,4 Ah.

Bộ này kế thừa điều kiện xả tham chiếu 0,2C từ bộ đã kiểm tra: dòng khoảng -0,48 A, đầu xả >=4 V, cuối xả gần 3 V, có kiểm tra dung lượng và tín hiệu. SOH = dung lượng tham chiếu / 2,4 × 100. Đặc trưng chỉ dùng 120 giây đầu xả; dung lượng toàn chu kỳ dùng làm nhãn, không làm đầu vào.

Hai giai đoạn thuộc cùng 86 pin. Phải chia huấn luyện/kiểm thử theo pin vật lý qua cả hai giai đoạn. Có ít mẫu chu kỳ hơn bộ lớn; đây là lựa chọn giảm quy mô xử lý, không phải bằng chứng chất lượng mô hình được giữ nguyên.

Chạy trên máy 16 GB: đọc từng file hoặc từng khối, huấn luyện bằng training_table.csv; không nạp toàn bộ dữ liệu đo vào RAM. Hiện bộ này chưa được áp dụng vào ứng dụng.
