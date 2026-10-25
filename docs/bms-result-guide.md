# Đọc kết quả BMS và demo pin giữ riêng

## Kết quả BMS

Tab **Dự đoán & đánh giá** mở trước. Chọn xe/phiên rồi bật dữ liệu mẫu, hoặc tải CSV cùng cấu hình BAIC EU500 145 Ah. Mẫu lấy đúng phiên đã chọn; CSV tải lên không tự gán vào xe trong bộ dữ liệu.

Kết quả gồm SOH ước tính; suy giảm so với danh định = 100 − SOH khi SOH không vượt 100%; dung lượng tương đương = SOH × 145/100 Ah; nhiệt độ nhỏ nhất/lớn nhất; điện áp bộ pin; dòng sạc; SOC; và chênh điện áp cell tại cùng thời điểm. Các thống kê tính trên toàn bộ cửa sổ tín hiệu tối đa 120 giây. Biểu đồ/bảng xem trước có thể lấy thưa nhưng giữ các cực trị nhiệt độ và chênh cell.

SOH là nhãn suy ra từ dòng điện/SOC khi sạc, chưa được đối chiếu phép đo dung lượng RPT độc lập. Dung lượng tương đương không phải phép đo dung lượng mới. Nếu SOH vượt 100%, phần suy giảm để trống và yêu cầu đối chiếu mốc danh định/SOC, không ghi độ chai âm.

## Ngưỡng đối chiếu

Không đặt mặc định các mốc nhiệt độ, độ lệch cell hoặc SOH thành tiêu chuẩn an toàn chung. Có thể nhập ngưỡng và ghi nguồn/ý nghĩa. Hệ thống chỉ so sánh số liệu với các tiêu chí này; chưa xác minh tài liệu người dùng nhập. Nhãn “chưa vượt tiêu chí” không phải xác nhận pin an toàn. Giới hạn kiểm tra cấu trúc CSV không phải giới hạn vận hành của hãng.

Không có mã lỗi BMS, điện áp định danh từng cell hoặc kết quả kiểm định thì không kết luận pin hỏng hay chỉ định cell hỏng. Báo cáo ghi rõ thông tin còn thiếu.

## Lịch sử và xuất báo cáo

Phiên mẫu có thể hiển thị nhãn dung lượng vận hành của các tháng trước tháng đang chọn; loại tháng hiện tại và tương lai. CSV người dùng tải lên chưa có lịch sử liên kết. Không tự suy diễn xu hướng chỉ từ một cửa sổ.

Tải bảng CSV hoặc báo cáo HTML mở độc lập. Mở HTML và chọn In → Lưu PDF nếu cần. Báo cáo chứa mô hình, nguồn đầu vào, số đo, ngưỡng, điểm cần đối chiếu và giới hạn diễn giải. Lịch sử dự đoán vẫn chỉ nằm trong tab trình duyệt.

## Demo pin giữ riêng

Random Forest học trên 85 pin; SDU_01 bị loại khỏi tập học ở cả hai giai đoạn. Chọn giai đoạn và chu kỳ → Chạy dự đoán → Hiện SOH tham chiếu và sai số. Đầu vào chỉ có 12 đặc trưng đã quy định, không có SOH tham chiếu/dung lượng nhãn. Có bảng đặc trưng, đóng góp theo đường đi cây và kết quả toàn giai đoạn. Mô hình demo tách khỏi mô hình bàn giao học lại toàn bộ dữ liệu.
