# Nội dung trình bày khóa luận

Tôi nghiên cứu ước lượng SOH từ 120 giây đầu chu kỳ xả. SOH tính bằng dung lượng xả tham chiếu chia 2,4 Ah và nhân 100. Đây là ước lượng sau khi đã quan sát đầu xả, không phải dự báo trước khi chu kỳ bắt đầu.

## Nội dung slide

| Phần | Nội dung | Minh chứng |
| --- | --- | --- |
| Bài toán | Nhu cầu ước lượng dung lượng bằng đoạn tín hiệu ngắn | Slide 1–2 |
| Dữ liệu | SDU 2025, 86 pin, hai giai đoạn; từ 145 triệu xuống 10.505.065 điểm giữ đủ các chu kỳ đã chọn | Slide 3–6, trang chất lượng |
| Phương pháp | 12 đặc trưng hoặc chuỗi V/I/T; không dùng dung lượng cuối làm đầu vào | Slide 7–8, mã features.py |
| Đánh giá | Giữ riêng pin qua cả hai giai đoạn, 5 vòng | Slide 9, split_assignments.csv |
| Kết quả | MAE, RMSE, R²; sai số theo pin và giai đoạn | Slide 10–14, reports/ |
| Sản phẩm | Tra cứu, so sánh, dự đoán và xuất kết quả | Slide 15–16, trình duyệt |
| Kết luận | Kết quả trong phạm vi thí nghiệm và hướng mở rộng | Slide 19–20 |

## Trình tự demo

Tôi mở Vincent D, chọn một giai đoạn ở Tổng quan và xem SOH theo chu kỳ. Ở Tra cứu pin, tôi chọn pin, chu kỳ và xem ba tín hiệu điện áp/dòng/nhiệt độ. Tôi so sánh hai chu kỳ để đối chiếu khác biệt.

Ở Đánh giá mô hình, tôi trình bày bảng kết quả giữ riêng pin và một ví dụ thực tế/dự đoán. Tôi phân biệt các dự đoán này với mô hình học lại toàn bộ dùng cho ứng dụng.

Ở Dự đoán SOH, tôi dùng CSV mẫu để trình diễn chức năng một chu kỳ và theo lô, sau đó tải phiếu kết quả. Mẫu có sẵn đã tham gia huấn luyện nên không được dùng để chứng minh khả năng dự đoán độc lập. Trang Chất lượng dữ liệu cho biết nguồn và các điểm nghi vấn.

## Các kết luận cần giữ đúng phạm vi

10.505.065 dòng là số điểm đo; mô hình bảng có 20.823 mẫu chu kỳ và 86 pin độc lập theo mã vật lý. Hai giai đoạn không tạo thành 172 pin độc lập. Giảm mật độ điểm sau 120 giây là lấy thưa, không phải kết luận tất cả điểm bị bỏ là nhiễu.

Random Forest đạt MAE 1,619 điểm phần trăm SOH trong cấu hình đã thử. GRU phức tạp hơn nhưng chưa tốt hơn trên bộ chọn này. Nguồn là thí nghiệm pin tại Trung Quốc, không phải xe đang vận hành tại Việt Nam. Bài hiện tại chưa dự báo RUL và chưa chứng nhận an toàn pin.

Phần giám sát xu hướng dùng slide 17: quy tắc lịch sử và Isolation Forest, 74 và 135 cờ xem xét theo hai giai đoạn. Không gọi các cờ là lỗi pin xác nhận. Chưa có dữ liệu BMS để kiểm chứng trên xe.

Slide 18: Ridge–RF phần dư, cách học trên train, kết quả MAE gần RF và RMSE hơi tăng. Không khẳng định mô hình hoàn toàn mới hoặc hiệu quả vượt trội.
