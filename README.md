# SDU — bản 10 triệu dòng giữ đủ chu kỳ

10.000.000 dòng đo xả; 20.823 chu kỳ tham chiếu; 86 pin vật lý; 172 CSV gzip.

## Giữ và giảm những gì

Giữ đủ các chu kỳ trong bộ đã chọn 30.929.675 dòng. Giữ mọi điểm đo trong 120 giây đầu xả và điểm cuối mỗi chu kỳ. Ở phần sau, lấy thưa theo thứ tự thời gian; số điểm được phân bổ theo độ dài chu kỳ. Không bỏ pin hoặc chu kỳ để đạt số dòng.

Từng dòng CSV được chọn giữ nguyên văn, gồm tên cột, cách viết số và thứ tự nguồn. Không sửa giá trị, điền thiếu, nội suy hoặc nhân bản. Hai ZIP nguồn và bộ 30,9 triệu dòng vẫn giữ riêng. Tập con này do dự án tạo, không phải gói gốc của tác giả.

Bảng training_table.csv và cycle_features.csv giữ nguyên file từ bộ đầy đủ. Dung lượng tham chiếu/SOH được tính từ chu kỳ đầy đủ; không tính lại dung lượng bằng tích phân trên đường đã lấy thưa. Đặc trưng chỉ dùng 120 giây đầu, được giữ đủ điểm. Giảm mật độ sau 120 giây làm mất chi tiết ở đoạn đó; không phù hợp nếu nghiên cứu khác cần nguyên chuỗi toàn chu kỳ.

## Kiểm tra chất lượng

Đã kiểm tra 30.929.675 dòng: không thiếu/vô hạn ở các tín hiệu chính, không có dòng trùng hoàn toàn, không có khóa thời gian trùng và không có giá trị ngoài các giới hạn kiểm tra đã công bố. Có 28 bước thời gian đi lùi trong thứ tự nguồn; khi tính đặc trưng đã sắp xếp bản sao trong chu kỳ, không sửa thứ tự file nguồn.

Bộ kiểm tra tìm được 65 nghi vấn xung đơn điện áp và 14 nghi vấn nhiệt độ, theo quy tắc so sánh hai điểm lân cận khi dòng ổn định. Đây là cờ xem xét, chưa xác nhận lỗi cảm biến; không tự sửa hay loại những điểm này chỉ dựa trên quy tắc. Danh sách nằm trong quality_spike_candidates.csv. Bản 10 triệu dòng giảm mật độ đoạn sau cửa sổ mô hình; không tuyên bố đã loại hết nhiễu.

## Sử dụng

Huấn luyện bằng training_table.csv (20.823 hàng), lấy đúng feature_columns trong dataset_summary.json. Không dùng dung lượng toàn chu kỳ, số điểm đo hoặc thông tin cuối chu kỳ làm đầu vào. Chia tập theo Battery_ID vật lý qua cả hai giai đoạn. Đọc file đo từng pin hoặc từng khối; không nạp tất cả vào RAM.

Nguồn: https://zenodo.org/records/14859405 — DOI 10.5281/zenodo.14859405, công bố 2025, CC BY 4.0. Wang, Gao và Tian: Deep sorting of reused batteries for enabling long-term consistency grouping with unknown prior conditions. Pin NMC(532)/graphite Lishen LR1865SZ, danh định 2,4 Ah.

Chưa áp dụng vào ứng dụng và chưa chạy mô hình mới. Script tái tạo cần thư mục selection (bộ lớn) và quality_review ở thư mục cha.

## Hồ sơ kiểm tra và trích dẫn

Xem KET_QUA_KIEM_TRA.md để biết kết quả kiểm tra thực tế trên bộ 10 triệu dòng và 25 điểm nghi vấn còn giữ. Trích dẫn đầy đủ tại NGUON_DU_LIEU.md. File CSV nguồn không bị sửa.
