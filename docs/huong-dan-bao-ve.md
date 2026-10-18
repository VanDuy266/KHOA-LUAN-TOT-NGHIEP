# Kịch bản bảo vệ và demo

## Trình bày khoảng 10–15 phút

1. Nêu mục tiêu ước lượng SOH sau 120 giây đầu xả; phân biệt SOH, SOC và RUL.
2. Trình bày nguồn NASA, bản lưu MATLAB và giới hạn chưa so byte với S3.
3. Phân biệt 2.089.048 phép đo với 636 mẫu SOH của 4 pin. Chỉ ra hai dòng sạc bị loại và nhật ký.
4. Giải thích nhãn theo 2 Ah và lý do không dùng capacity làm đặc trưng.
5. Trình bày bốn vòng giữ riêng pin; fit trên ba pin, test pin còn lại.
6. So sánh kết quả thật theo từng pin, bao gồm trường hợp Ridge tốt hơn RF và Signal Ridge thất bại.
7. Nêu phân tích thời gian: RF kém baseline SOH cuối đã biết, không tuyên bố dự đoán RUL.
8. Chạy demo qua 5 mục: Tổng quan → Tra cứu pin → Đánh giá mô hình → Dự đoán SOH → Hồ sơ đề tài. Thử lọc chu kỳ, chọn mô hình, upload CSV và tải kết quả tiếng Việt.
9. Kết luận đúng phạm vi, nói rõ chưa có dữ liệu Việt Nam hoặc xe thực tế.

## Câu hỏi thường gặp

**Vì sao có hai triệu dòng mà chỉ 636 mẫu?** Mỗi dòng là một thời điểm; nhãn dung lượng thuộc toàn bộ chu kỳ xả. Một chu kỳ tạo một mẫu SOH. Phần sạc chưa tự có nhãn SOH.

**Dataset Việt Nam không?** Không. Đây là dữ liệu thử nghiệm NASA. Chưa xác minh được nguồn Việt Nam công khai tương đương; không đổi tên nguồn để tạo cảm giác dữ liệu trong nước.

**Tại sao không random split?** Các thời điểm và chu kỳ cùng pin tương quan. Chia theo pin phù hợp câu hỏi tổng quát hóa sang pin chưa quan sát.

**SOH lớn hơn 100% có lỗi không?** Không nhất thiết. Dung lượng đo có thể vượt danh định 2 Ah; giữ đúng nhãn, không tự cắt.

**Kết quả 1,24 trước đây còn dùng không?** Không dùng để mô tả bộ bốn pin. Bộ hiện tại phải dùng bảng metrics mới, RF macro MAE khoảng 2,724 điểm phần trăm SOH.

**Có độ chính xác 97,276% không?** Không suy từ MAE như vậy. MAE là sai số tuyệt đối theo điểm phần trăm SOH.

**RF có luôn tốt nhất không?** Không. Cycle Ridge tốt hơn RF ở B0005, và RF kém baseline cuối đã biết trong kiểm thử theo thời gian.

**Tại sao chưa dùng được trên xe?** Dữ liệu là cell thử nghiệm, chưa có pack, điều kiện thực địa và đánh giá trên xe điện.

**Chọn mô hình thế nào?** RF đã được định trước cho demo. Tham số cố định; phân tích bổ sung không dùng để chọn lại trên test. Tối ưu tiếp cần validation đúng thiết kế.

## Trước khi nộp

Giảng viên cần xác nhận nguồn dữ liệu, phạm vi tổng quan nghiên cứu, mẫu trường, số trang, cách trích dẫn và thời hạn. Sinh viên cần chạy lại, hiểu nội dung và kiểm tra mọi kết quả. Không tạo thay chữ ký, nhận xét hoặc xác nhận nghiệm thu.
