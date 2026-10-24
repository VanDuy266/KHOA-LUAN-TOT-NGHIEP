## 4.11. Thực nghiệm bổ sung trên nguồn XJTU

Chọn 23 pin thuộc Batch-1/2 trong 55 pin XJTU. Đã tải và kiểm tra CRC/SHA-256 của 23 thành viên MAT nguyên gốc từ ZIP tác giả. Tổng 46.215.511 điểm đo. 6.961 phần tử chu kỳ; 6.961 chu kỳ đạt kiểm tra đầu vào. 0 chu kỳ bị loại. 59 phép đo trùng giây được gộp trung bình trong cửa sổ dẫn xuất.

Không dùng 23 chu kỳ đầu 0,2C trong đánh giá chính; còn 6,938 chu kỳ xả 1C. Dùng SOH theo 2 Ah và 11 đặc trưng chung, chuẩn hóa dòng theo dung lượng danh định; không sửa dữ liệu nguồn. Giữ riêng 23 mã pin qua 5 vòng, seed 42, cấu hình cố định.

| model | mae | rmse | r2 |
| --- | --- | --- | --- |
| Mean baseline | 3.759 | 4.720 | -0.057 |
| Ridge | 0.971 | 1.205 | 0.920 |
| Random Forest | 0.577 | 0.764 | 0.965 |
| LightGBM | 0.596 | 0.787 | 0.964 |
| Ridge-RF residual | 0.666 | 0.828 | 0.960 |
| RF multi-source | 0.623 | 0.867 | 0.945 |
| GRU | 1.240 | 1.543 | 0.856 |

Random Forest riêng XJTU đạt MAE 0.577, RMSE 0.764, R² 0.965. RF đa nguồn đạt MAE 0.623, RMSE 0.867, R² 0.945. MAE tăng 0.047 điểm phần trăm SOH khi thêm nguồn SDU trong cấu hình đã cố định. Đây là thực nghiệm thăm dò trên cùng phân hoạch, chưa phải bằng chứng ưu thế thống kê hoặc cải thiện trên mọi điều kiện.

![Dự đoán RF trên hai pin XJTU giữ riêng](../reports/xjtu/held_out_predictions.png)

Chuyển miền chỉ học trên SDU, không dùng nhãn XJTU:

| model | mae | rmse | r2 |
| --- | --- | --- | --- |
| RF normalized | 42.654 | 42.910 | -89.595 |
| RF original SDU | 12.836 | 13.649 | -8.045 |

Các phép kiểm tra batch và bảng theo từng pin nằm trong reports/xjtu và docs/thuc-nghiem-xjtu.md. Kết quả vẫn thuộc tế bào trong phòng thí nghiệm; chưa là bằng chứng mô hình dùng được trên xe.
