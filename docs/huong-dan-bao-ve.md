# Hướng dẫn trình bày và demo

## Kịch bản 10–15 phút

1. Nêu mục tiêu ước lượng SOH từ 120 giây đầu xả và phân biệt SOH/SOC/RUL.
2. Giới thiệu nguồn chuyển đổi, ba pin chính, 468 chu kỳ và hạn chế chưa đối chiếu dữ liệu gốc.
3. Minh họa cách tạo nhãn và lý do không đưa capacity vào đặc trưng.
4. Giải thích giữ riêng từng pin làm kiểm thử; nhấn mạnh mô hình chưa thấy pin kiểm thử.
5. So sánh MAE/RMSE, xem kết quả theo pin, diễn giải đơn vị điểm phần trăm.
6. Chạy demo bằng CSV mẫu; nói rõ mẫu đã nằm trong dữ liệu huấn luyện demo.
7. Kết thúc bằng giới hạn và kế hoạch xác minh nguồn gốc, thêm pin và dữ liệu xe thực tế.

## Câu hỏi có thể gặp

**Vì sao không chia ngẫu nhiên?** Chu kỳ cùng pin có tương quan. Chia theo pin phù hợp câu hỏi tổng quát hóa sang pin chưa quan sát.

**SOH ước lượng lúc nào?** Sau 120 giây đầu bản ghi xả; không dự đoán trước khi xả.

**Có dùng nhãn làm đầu vào không?** Không. Dung lượng và SOH chỉ dùng xác minh biến đích; dữ liệu sau cửa sổ không dùng tạo đặc trưng.

**1,24 là độ chính xác bao nhiêu phần trăm?** Đây là MAE 1,24 điểm phần trăm SOH, không chuyển thành “độ chính xác 98,76%”.

**Dùng được trên xe điện chưa?** Chưa có bằng chứng. Dữ liệu là cell thử nghiệm chuyển đổi, chưa có dữ liệu bộ pin trên xe.

**Vì sao chỉ ba pin?** Phạm vi chính chọn trước khi chạy mô hình; các pin bổ sung có nhãn cực thấp hoặc bằng 0 cần xác minh. Không tuyên bố đại diện cho mọi pin.

**Trục thời gian giống nhau có ý nghĩa gì?** Là dấu hiệu chất lượng cần đối chiếu MAT gốc. Chưa xác định nguyên nhân, không bỏ qua hạn chế trong kết luận.

**Đã tối ưu mô hình chưa?** Chưa. Tham số cố định; lựa chọn siêu tham số cần validation hoặc nested validation khi mở rộng.

## Những việc cần giảng viên xác nhận trước khi nộp

- Chấp nhận dữ liệu, hoặc yêu cầu dùng dữ liệu gốc thay bản chuyển đổi.
- Mẫu trang bìa, bố cục, độ dài, cách trích dẫn và thời hạn chính thức.
- Mức độ cần thiết của tổng quan nghiên cứu, ablation và thực nghiệm bổ sung.
- Nội dung, số liệu và phạm vi kết luận sau khi sinh viên kiểm tra và hiểu mã nguồn.

Không tạo chữ ký, nhận xét, lời cam đoan hoặc xác nhận nghiệm thu thay cho người có trách nhiệm.
