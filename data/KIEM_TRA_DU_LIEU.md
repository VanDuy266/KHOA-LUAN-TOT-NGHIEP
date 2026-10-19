# Kết quả kiểm tra bộ SDU 10 triệu dòng

## Kết luận

Đạt các kiểm tra cấu trúc, tính toàn vẹn và tính nhất quán của bảng đặc trưng/nhãn đã thực hiện. Có thể dùng làm đầu vào cho bước huấn luyện thực nghiệm theo thiết kế 120 giây đầu xả. Chưa khẳng định toàn bộ tín hiệu không có nhiễu.

| Kiểm tra trên file thực tế | Kết quả |
| --- | ---: |
| File CSV gzip | 172 |
| Dòng đo xả | 10.000.000 |
| Chu kỳ tham chiếu | 20.823 |
| Pin vật lý | 86 |
| Dòng thiếu hoặc vô hạn ở tín hiệu chính | 0 |
| Dòng ngoài giới hạn kiểm tra | 0 |
| Dòng trùng hoàn toàn | 0 |
| Khóa thời gian trùng trong pin/chu kỳ | 0 |
| Chu kỳ sai số dòng so với phân bổ | 0 |
| Chu kỳ có đặc trưng 120 giây đầu không khớp | 0 |
| Chu kỳ có dung lượng tham chiếu không khớp | 0 |
| Điểm đo trong 120 giây đầu | 261.516 |
| File khớp SHA-256 của nội dung CSV đã xuất | 172/172 |

## Phạm vi kiểm tra

Đọc toàn bộ 172 CSV thực tế và kiểm tra mã pin, chu kỳ, thời gian, điện áp, dòng điện, nhiệt độ, dung lượng. Giới hạn kiểm tra: thời gian không âm; điện áp (0;4,5] V; nhiệt độ [-40;100] °C; dung lượng không âm ngoài sai số 10^-6 Ah. Đây là ngưỡng kỹ thuật kiểm tra cell, không thay thế xác thực cảm biến của tác giả.

Tính lại 12 đặc trưng theo từng chu kỳ từ dữ liệu CSV 10 triệu dòng; đối chiếu bảng đã lưu với dung sai số thực 10^-10. Đối chiếu dung lượng xả ghi trong các điểm giữ lại với nhãn của chu kỳ đầy đủ. Bảng dùng cho mô hình không có giá trị thiếu/vô hạn và không trùng khóa giai đoạn + pin + chu kỳ. Trong gói nguồn riêng, mã kiểm tra nằm trong verification/verify_dataset.py. Sản phẩm lưu bản sao hồ sơ tại data/provenance/verification/; kiểm tra Parquet bằng scripts/check_dataset.py.

## Các trường hợp cần lưu ý

- Bộ 30,9 triệu dòng có 79 cờ nghi vấn xung đơn: 65 điện áp và 14 nhiệt độ. Cờ được tạo bằng quy tắc so sánh điểm với hai hàng xóm khi dòng tương đối ổn định; không phải kết luận chắc chắn lỗi cảm biến.
- Bản 10 triệu dòng còn 25 bản ghi khớp các cờ đó; tất cả nằm sau 120 giây đầu xả. Không có cờ đã nhận diện này trong cửa sổ dùng tính đặc trưng. Không tự sửa hoặc xóa 25 điểm khi chưa xác định nguyên nhân. Danh sách thực tế nằm trong verification/retained_spike_candidates.csv.
- Có 23 bước thời gian đi lùi trong thứ tự dòng nguồn của bản 10 triệu dòng. Không trùng khóa thời gian; khi tính đặc trưng, sắp xếp bản sao theo thời gian trong từng chu kỳ. Thứ tự và giá trị trong CSV nguồn được giữ nguyên, không ghi đè để làm đẹp dữ liệu.
- Điện trở trong có nhiều ô trống theo cách ghi đo của nguồn. Cột này được giữ nguyên trong CSV nhưng không thuộc bộ đặc trưng mô hình. Kết luận “không thiếu” ở bảng trên áp dụng cho các tín hiệu chính đã liệt kê, không áp dụng mọi cột tùy chọn.
- Bản 10 triệu dòng đã lấy thưa đoạn sau 120 giây, nên giảm độ chi tiết ở đoạn đó. Nhãn SOH vẫn lấy từ chu kỳ đầy đủ; không tích phân lại đường lấy thưa để thay nhãn.

## Sử dụng trong khóa luận

Nguồn và trích dẫn nằm trong data/README.md của sản phẩm, hoặc NGUON_DU_LIEU.md của gói nguồn riêng. SOH (%) = dung lượng tham chiếu / 2,4 × 100. Dùng training_table.csv, đúng danh sách feature_columns trong dataset_summary.json. Chia theo Battery_ID vật lý qua cả hai giai đoạn để tránh rò rỉ dữ liệu. Không dùng dung lượng toàn chu kỳ hoặc thông tin cuối chu kỳ làm đầu vào dự đoán từ 120 giây đầu.

Kiểm tra dữ liệu tách biệt với đánh giá mô hình. Kết quả Ridge, Random Forest, LightGBM và GRU, cùng mốc đối chứng, được lưu trong reports/ của sản phẩm Vincent D.
