# Kế hoạch kiểm chứng bằng dữ liệu BMS

## Trạng thái

Đã tải dữ liệu BMS sạc của 20 xe BAIC EU500 vận hành thực tế từ nhóm Deng và cộng sự (2023), và triển khai thực nghiệm riêng trong ứng dụng. Nhãn SOH được suy ra từ dòng điện và SOC, không phải dung lượng đo bằng RPT độc lập. Vì vậy chưa được gọi là kiểm chứng SOH vật lý độc lập trên xe. Kết quả SDU vẫn là thí nghiệm cell trong lab. Xem [Thực nghiệm BMS](thuc-nghiem-bms.md) để phân biệt nguồn, nhãn và thiết kế đánh giá.

## Dữ liệu cần thu thập

| Trường | Nội dung |
| --- | --- |
| Mã xe/bộ pin/tế bào | Mã ẩn danh để giữ riêng thiết bị khi kiểm thử |
| Thời gian | Mốc đo và đơn vị giây, thông tin múi giờ |
| Điện áp | Điện áp từng tế bào, đơn vị V; điện áp cả bộ pin lưu riêng |
| Dòng điện | A, quy ước dấu sạc/xả và vị trí đo |
| Nhiệt độ | °C, vị trí cảm biến, phân biệt bề mặt tế bào và môi trường |
| Hóa học, dung lượng danh định | Thông tin tế bào và bộ pin, cấu hình nối tiếp/song song |
| Chu kỳ, trạng thái vận hành | Mã chu kỳ, sạc/xả/nghỉ, thời điểm bắt đầu xả |
| Dung lượng tham chiếu | Phép đo Ah độc lập và điều kiện đo để đối chiếu SOH |
| Nhật ký bất thường | Nhãn kiểm tra của kỹ thuật viên, thời điểm, căn cứ xác nhận |

SOH ước tính sẵn từ BMS không tự trở thành nhãn SOH đo độc lập. Cần mô tả cách tạo nhãn, sai số thiết bị, điều kiện dòng/nhiệt độ và những phép đo còn thiếu.

## Quy trình đánh giá dự kiến

1. Xác nhận dữ liệu ở cấp tế bào hay bộ pin và kiểm tra đơn vị, quy ước dấu, đồng bộ thời gian.
2. Đánh giá sự khác biệt với SDU: hóa học, dòng xả, nhiệt độ, dung lượng danh định và mật độ lấy mẫu.
3. Tạo nhãn tham chiếu phù hợp với pin thực tế; giữ riêng xe/bộ pin khi kiểm thử. Chỉ huấn luyện hoặc hiệu chỉnh trên phần được dành cho học.
4. Đánh giá MAE/RMSE/R² theo thiết bị, kèm điều kiện đo và khoảng SOH. Không chọn cấu hình bằng điểm các xe kiểm thử.
5. Với phát hiện bất thường, chỉ tính precision/recall khi có nhãn xác nhận và quy tắc đối chiếu thời điểm rõ ràng. Nếu chưa có nhãn, chỉ báo cáo cờ xem xét.

Mô hình hiện tại dùng tế bào 2,4 Ah và cửa sổ xả tham chiếu SDU. Không đưa trực tiếp điện áp bộ pin hoặc nhãn có mẫu số khác vào mô hình đó. Kiểm chứng xe có thể cần mô hình được huấn luyện hoặc hiệu chỉnh lại; chưa có bằng chứng chuyển giao trực tiếp.

## Khảo sát nguồn công khai

Đã tải và kiểm tra bảng SOH trên xe thực tế tại Zenodo 22643868: 3.171 bản ghi, 15 cột. Bảng không có chuỗi điện áp/dòng điện/nhiệt độ để kiểm thử trực tiếp mô hình SDU. Đã khảo sát thêm dữ liệu BMS LFP năm 2024 tại Zenodo 13715694; chưa tải toàn bộ và chưa kiểm chứng mô hình trên bộ này. Chi tiết phạm vi, nguồn và kết quả kiểm tra: [Phạm vi và dữ liệu kiểm thử bổ sung](pham-vi-va-du-lieu-kiem-thu.md).

Kết quả tìm nguồn phù hợp hơn: [Lựa chọn dữ liệu ngoài cho bài toán SOH](lua-chon-du-lieu-ngoai.md). Đã đọc mẫu CSV NMC LG Chem E71A có đủ loại tín hiệu và dung lượng, nhưng là dữ liệu lab 69,5 Ah, chưa kiểm thử mô hình SDU trực tiếp.
