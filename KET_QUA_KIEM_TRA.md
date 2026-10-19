# Kết quả kiểm tra bộ SDU được chọn

Quy tắc: giữ toàn bộ điểm 120 giây đầu và điểm cuối chu kỳ, giữ mỗi ba điểm còn lại một điểm theo thứ tự thời gian. Số dòng là kết quả đếm, không đặt trước.

| Kiểm tra | Kết quả |
| --- | ---: |
| Dòng đo | 10,505,065 |
| Chu kỳ | 20,823 |
| Pin vật lý | 86 |
| File CSV gzip | 172 |
| Thiếu/vô hạn ở tín hiệu bắt buộc | 0 |
| Ngoài ngưỡng kiểm tra | 0 |
| Dòng trùng hoàn toàn | 0 |
| Khóa thời gian trùng | 0 |
| Chu kỳ có đặc trưng không khớp | 0 |
| Chu kỳ có nhãn không khớp | 0 |
| Sai số dòng theo quy tắc chọn | 0 |
| Điểm trong 120 giây đầu | 261,516 |
| Bước thời gian đi lùi trong thứ tự nguồn | 23 |
| Điểm nghi vấn còn giữ | 26 |
| Điểm nghi vấn trong cửa sổ mô hình | 0 |

## Phạm vi

Đã đọc đủ 172 CSV và đối chiếu SHA-256 của nội dung giải nén. Tính lại 12 đặc trưng và dung lượng tham chiếu cho đủ 20.823 chu kỳ. Tín hiệu bắt buộc gồm thời gian, điện áp, dòng điện, nhiệt độ, dung lượng và mã pin/chu kỳ. Các cột tùy chọn như điện trở trong có thể trống theo cách ghi của tác giả, không được dùng làm đặc trưng.

Giới hạn: thời gian không âm, điện áp (0; 4,5] V, nhiệt độ [-40; 100] °C, dung lượng không âm ngoài sai số 10^-6 Ah. Không có lỗi theo các kiểm tra này không có nghĩa hoàn toàn không có nhiễu.

26 cờ nghi vấn được giữ, không tự sửa hoặc xóa. Không cờ nào trong cửa sổ 120 giây đầu. Cờ theo quy tắc biến thiên tín hiệu, chưa kết luận lỗi cảm biến. Nguồn giữ nguyên thứ tự; bản sao phục vụ mô hình được sắp thời gian trong chu kỳ. Có 23 bước đi lùi trong thứ tự nguồn.

Nhãn SOH lấy từ chu kỳ đầy đủ trước lấy thưa: dung lượng / 2,4 Ah × 100. Bảng đặc trưng và nhãn giữ nguyên so với bộ 30.929.675 dòng. Không tính lại nhãn bằng đường lấy thưa. Không dùng dung lượng hoặc tín hiệu cuối chu kỳ làm đầu vào. Chia tập theo pin vật lý qua cả hai giai đoạn.

Trích dẫn tại NGUON_DU_LIEU.md. Nhật ký nằm trong verification/, source_preservation_audit.csv và cycle_sampling_audit.csv. Đây là tập con do dự án tạo từ SDU, không phải nguyên gói của tác giả. Kết quả dự đoán được đánh giá riêng trong sản phẩm Vincent D.
