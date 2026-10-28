# Giải thích dự đoán và kiểm chứng ngưỡng dung lượng

## Phạm vi
SDU là bài toán chính; BAIC dùng nhãn dung lượng vận hành suy ra. Không ghép dữ liệu lỗi của 99 xe vào cùng xe BAIC. Không tuyên bố mô hình áp dụng mọi hóa học pin.

## Giải thích đầu ra
Random Forest: phân rã theo đường đi trong cây. Ridge–RF: tổng thành phần Ridge đã chuẩn hóa và đóng góp cây phần dư. Đây không phải SHAP. CatBoost dùng ShapValues gốc; XGBoost dùng pred_contribs của thư viện.

Web hiển thị mốc, tổng đóng góp, đầu ra tái dựng, sai lệch với dự đoán và ba đặc trưng đóng góp lớn nhất cùng giá trị đầu vào. Tất cả đặc trưng vẫn có trong biểu đồ. Đơn vị đóng góp là điểm phần trăm SOH. Không suy diễn đóng góp thành cơ chế nhân quả của sự chai pin.

Kiểm tra tự động xác nhận phép cộng tái dựng trên mẫu của từng mô hình đang phục vụ; không dùng kiểm tra này thay đánh giá độ chính xác dự đoán.

## Chất lượng và tốc độ
MAE/RMSE/R² lấy từ dự đoán ngoài tập huấn luyện đã lưu. Tốc độ lấy từ timings.csv: tổng thời gian dự đoán / tổng số mẫu ở các vòng có đo; thời gian học là trung bình theo vòng. GRU thiếu thời gian dự đoán thì để trống. Số đo batch không phải độ trễ một yêu cầu web; các lượt chạy chưa bảo đảm cùng phần cứng và ngân sách tối ưu.

## Dự báo tới mốc
OLS tối đa 20 mốc lịch sử gần nhất; chia theo thời gian ở 60%, 70%, 80%; tương lai chỉ dùng đối chiếu. Chỉ báo dự đoán khi đáp ứng điều kiện xu hướng đã công bố. Xem reports/health/validation.md và chronological_results.csv để tái lập.

MAE thời điểm chỉ tính trên các lượt vừa có dự báo vừa quan sát chạm ngưỡng: SDU 137 lượt, khoảng 27,67 chu kỳ; BMS 42 lượt, khoảng 3,29 tháng. Đây là lượt cắt, không phải số pin độc lập. Không so trực tiếp hai đơn vị; không coi MAE có điều kiện là chất lượng trên toàn bộ pin. Chưa có khoảng dự đoán hiệu chuẩn. Mốc 80% là mốc dung lượng nghiên cứu, không phải ngày hỏng hoặc giới hạn an toàn.

## Chưa bổ sung
Không ép ICA/DVA từ đoạn 120 giây thiếu miền điện áp phù hợp. Không thêm Transformer khi chưa có thiết kế và dữ liệu kiểm thử tương ứng. Không gọi hệ thống là mô hình dùng cho mọi loại pin.


## Đối chiếu sáu tiêu chí Data Science

| Tiêu chí | Bằng chứng hiện có | Giới hạn cần trình bày |
|---|---|---|
| Chống rò rỉ | Kiểm thử nhóm theo pin vật lý/xe; hai giai đoạn SDU cùng nhóm; pin demo giữ riêng; dấu vết verification.json | Kiểm tra từ OOF và nguồn mã, chưa phải huấn luyện tái lập hoàn toàn độc lập. Không coi chia theo thời gian và giữ riêng pin là cùng bài toán. |
| Đặc trưng miền | 120 giây đầu xả/sạc; thống kê điện áp, dòng, nhiệt độ, độ dốc; chu kỳ và giai đoạn cho SDU | Không phải mô hình cơ chế điện hóa; ICA/DVA bổ sung trên sáu đoạn xả đầy đủ đủ điều kiện; không đưa vào mô hình đầu xả 120 giây. |
| So sánh công bằng | Cùng mẫu kiểm thử và MAE/RMSE/R² theo pin/xe; bảng thời gian thực nghiệm | Ngân sách tinh chỉnh và phần cứng chưa bảo đảm đồng nhất; thiếu thời gian GRU để trống. |
| Giải thích | Đóng góp cục bộ có tái dựng đầu ra; CatBoost/XGBoost có SHAP gốc | RF/Ridge–RF không gọi là SHAP. Đã có SHAP tổng hợp mô tả 516 mẫu CatBoost cuối; không phải đánh giá ngoài tập học. Không suy nhân quả. |
| Tổng quát hóa và sản phẩm | Web và ánh xạ CSV/CSV.GZ, đổi đơn vị; SDU và BAIC đánh giá riêng | Đã kiểm thử SDU → NASA trên 636 chu kỳ của bốn cell; chuyển miền kém. Chưa kiểm thử MIT. Ánh xạ không xác nhận tương thích. Chưa hỗ trợ XLSX/MAT/JSON. |
| Phản biện và giới hạn | Phân biệt SOH/SOC/lỗi; nêu nhãn BMS suy ra, phạm vi dữ liệu và đánh giá ngưỡng có điều kiện | Không chứng nhận an toàn, không khẳng định ngày hỏng hoặc áp dụng mọi loại pin. |

Các tiêu chí này là bảng tự đối chiếu kỹ thuật, không thay quy định của trường hoặc đánh giá của giảng viên. Không sử dụng con số “80% sinh viên mắc lỗi” vì chưa có nguồn kiểm chứng.

## Quy trình tổng quát hóa chéo bộ dữ liệu — NASA đã thực nghiệm, MIT chưa chạy

1. Xác minh nguồn, giấy phép, hóa học pin, dung lượng, chế độ đo và định nghĩa nhãn của từng bộ; giữ nguyên mã cell và nguồn dữ liệu.
2. Chốt bài toán, cùng cửa sổ tín hiệu và nhãn SOH. Chỉ đổi đơn vị/tên cột không làm các điều kiện đo tương đương.
3. Tất cả chuẩn hóa học từ dữ liệu train; mọi chu kỳ của một cell cùng phía; chọn tham số chỉ bằng train/validation nội bộ. Bộ kiểm thử ngoài phải không tham gia lựa chọn đặc trưng hay mô hình.
4. Báo riêng: kiểm thử trong nguồn trên cell giữ riêng; zero-shot sang nguồn khác; mô hình gộp kiểm thử trên toàn bộ nguồn giữ riêng. Nếu điều chỉnh theo nhãn nguồn đích, ghi rõ là thích nghi miền, không gọi zero-shot.
5. Báo số cell và mẫu, tỷ lệ dữ liệu bị loại, MAE/RMSE điểm % SOH, R², kết quả theo từng cell và khoảng bất định theo nhóm. Không điền số minh họa thành kết quả.
6. Chỉ đưa mô hình mới vào lựa chọn của ứng dụng sau khi có artifact, metadata nguồn/splits và kết quả kiểm chứng; đưa dung lượng danh định vào đầu vào không tự bảo đảm tổng quát hóa.

Ánh xạ hiện tại chuẩn hóa một đoạn xả số sang giây, V, A, °C; có xác nhận dấu dòng xả. Timestamp ngày giờ cần đổi thành thời gian số trước khi tải. Không trộn nhiều chu kỳ hoặc đổi điện áp pack thành cell bằng cách đặt lại tên cột.


## Cập nhật thực nghiệm
SHAP tổng hợp, ICA/DVA sáu đoạn xả và kiểm chứng NASA đã được bổ sung. Phạm vi, kết quả tốt/chưa tốt, hash và tái lập ở reports/research/protocol.md; thay thế các ghi chú kế hoạch cũ về ba phần này. Không có mô hình mọi loại pin hoặc chẩn đoán an toàn tuyệt đối.
