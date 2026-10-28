# Bản trình bày kết quả và chuẩn bị bảo vệ

Báo cáo kết quả thực nghiệm, nguồn nhãn, thiết kế kiểm thử và phạm vi kết luận của đề tài.

## 1. Mục tiêu và phạm vi

Ước tính trạng thái sức khỏe dung lượng SOH từ tín hiệu ngắn đầu chu kỳ; đánh giá khả năng dự đoán trên pin/xe không tham gia huấn luyện; triển khai công cụ tra cứu, dự đoán và xuất kết quả. Phần chính là hồi quy SOH. SDU tế bào pin và BMS bộ pin xe được xây dựng, huấn luyện và đánh giá riêng. Phần mở rộng gồm ngoại suy ngưỡng dung lượng và phân loại dấu hiệu lỗi trên dữ liệu điện áp Zenodo riêng; không chứng nhận an toàn.

## 2. Nguồn và ý nghĩa SOH tham chiếu

| Nội dung | SDU | BMS trên xe |
|---|---|---|
| Nguồn | Shandong University, Zenodo DOI 10.5281/zenodo.14859405 | BatICM, battery-charging-data-of-on-road-electric-vehicles; bài báo DOI 10.1016/j.apenergy.2023.120954 |
| Đối tượng | 86 tế bào pin, hai giai đoạn, 20.823 chu kỳ được chọn | 20 xe BAIC EU500, 27.205 phiên đủ điều kiện, 569 nhãn xe–tháng |
| Mốc dung lượng | 2,4 Ah | 145 Ah |
| Nhãn | Dung lượng xả tham chiếu từ cột Discharge_Capacity(Ah) trong chu kỳ xả được chọn; SOH = Q/2,4 × 100 | Dung lượng tương đương suy ra từ phần đuôi sạc: Q = tích phân độ lớn dòng sạc theo giờ / (độ tăng SOC/100); SOH = trung vị Q theo xe–tháng /145 × 100 |
| Kiểm tra nhãn | Đối chiếu dung lượng nguồn với tích phân dòng xả trong mã chọn dữ liệu; sai lệch không quá max(0,02 Ah; 2% dung lượng) | Đuôi sạc sau 120 giây, ít nhất 100 điểm, SOC tăng ít nhất 20 điểm %, ít nhất 3 phiên mỗi xe–tháng |
| Đầu vào | Tín hiệu 120 giây đầu xả, mã giai đoạn và số chu kỳ | Tín hiệu 120 giây đầu sạc; không đưa dung lượng khả dụng, nhãn tham chiếu, mã xe hoặc thời gian tuyệt đối vào đặc trưng |

SDU dùng dung lượng nguồn, không phải một phép đo mới do đề tài thực hiện. BMS phụ thuộc độ chính xác SOC, cảm biến dòng, điều kiện sạc và giả định quy đổi dung lượng qua mức tăng SOC. Trung vị theo tháng giảm ảnh hưởng ngoại lai nhưng không loại bỏ sai lệch có hệ thống. Nhiều phiên dùng cùng nhãn tháng nên không phải các phép đo dung lượng độc lập. Nhãn tháng có thể dùng dữ liệu sau ngày phiên dự đoán: phù hợp đánh giá hồi cứu theo xe giữ riêng, không được gọi là kiểm chứng dự báo thời gian thực chỉ dùng quá khứ. Chưa có phép đo RPT độc lập để xác nhận SOH vật lý BMS.

Nguồn: https://doi.org/10.5281/zenodo.14859405 và https://github.com/BatICM/battery-charging-data-of-on-road-electric-vehicles . Mã đối chiếu: data/provenance/rebuild/selection/select_sdu.py, scripts/prepare_data.py, src/battery_soh/bms.py, scripts/build_bms.py.

## 3. Thiết kế so sánh

Chia 5 vòng theo pin vật lý SDU hoặc xe BMS; không chia ngẫu nhiên các dòng của cùng một pin sang hai phía. Hai giai đoạn của cùng pin SDU nằm chung nhóm. Các mô hình trong mỗi bộ dùng cùng mẫu và cùng vòng kiểm thử. Chuẩn hóa được fit trên tập học. CatBoost/XGBoost có nhóm validation bên trong tập học để chọn siêu tham số; baseline cấu hình cố định, nên chưa cân bằng ngân sách tinh chỉnh. GRU dùng chuỗi thay cho bảng đặc trưng, vì vậy không thể quy toàn bộ chênh lệch cho thuật toán.

MAE/RMSE báo bằng điểm % SOH, thấp hơn tốt hơn; R² cao hơn tốt hơn nhưng không phải phần trăm chính xác. Bảng chính dùng trung bình đều theo pin/xe. Chỉ số gộp có trọng số ngầm theo số chu kỳ và có thể đổi thứ hạng.

## 4. Kết quả và mức cải thiện

| Bộ dữ liệu | Mô hình | MAE | RMSE | R² |
|---|---|---:|---:|---:|
| SDU | Ridge–RF | 1,6122 | 2,1599 | 0,9708 |
| SDU | Random Forest | 1,6189 | 2,1572 | 0,9705 |
| BMS | Ridge–RF | 2,0998 | 2,7292 | 0,5043 |
| BMS | Random Forest | 2,1720 | 2,8316 | 0,4674 |

SDU: Ridge–RF giảm MAE 0,0067 điểm %, tương đương khoảng 0,41% so với MAE Random Forest; cải thiện 40/86 pin. Khoảng bootstrap mô tả cho chênh MAE [-0,0470; 0,0304] chứa 0: chưa có căn cứ tuyên bố vượt trội chắc chắn. Random Forest lại có RMSE macro thấp hơn và MAE gộp tốt hơn. Vì vậy cần nói “thấp nhất theo MAE macro trong cấu hình đã thử”, không nói “tốt nhất mọi tiêu chí”.

BMS: Ridge–RF giảm MAE 0,0722 điểm %, khoảng 3,33% so với Random Forest; cải thiện 20/20 xe trong kết quả đã lưu. Khoảng bootstrap mô tả [-0,0947; -0,0516] không chứa 0, là bằng chứng cải thiện nhất quán trong tập xe này; chưa suy rộng mọi đội xe hoặc mọi loại pin. Bootstrap tái lấy mẫu theo xe/pin, không điều chỉnh phụ thuộc do tập học CV dùng chung và việc thử nhiều mô hình.

Không lấy 100 − MAE làm “độ chính xác”. Không so trực tiếp điểm SDU và BMS để kết luận bộ nào tốt hơn vì khác đối tượng và cách tạo nhãn. Toàn bộ 8 mô hình SDU và 4 mô hình BMS nằm trong CSV và bản kết quả đi kèm; không chỉ trình bày hai mô hình tốt nhất.

## 5. Đóng góp

- Quy trình chọn và kiểm tra dữ liệu, trích xuất tín hiệu đầu chu kỳ, giữ nhãn tách khỏi đầu vào.
- So sánh các cấu hình trên cùng nhóm kiểm thử và công bố dự đoán ngoài tập học, sai số theo pin/xe, hash và công cụ kiểm chứng.
- Tích hợp mô hình đã đánh giá vào giao diện, demo pin giữ riêng, dữ liệu BMS riêng và báo cáo tải về.

Ridge–RF là phối hợp thuật toán đã có, không tuyên bố phát minh thuật toán mới. Đóng góp nằm ở quy trình và kiểm chứng trong phạm vi đề tài.

## 6. Hạn chế và hướng tiếp theo

Mẫu pin/xe còn giới hạn; chia theo nhóm chưa chứng minh dự đoán tương lai; BMS thiếu dung lượng đo độc lập và nhãn lỗi; ngân sách tinh chỉnh mô hình chưa ngang nhau. Audit tính lại tệp dự đoán và kiểm tra mã nguồn, không thay thế tái huấn luyện độc lập. Do tập kiểm thử đã được xem để so sánh mô hình, cần tập ngoài chưa dùng lựa chọn hoặc nested CV toàn bộ quy trình nếu muốn đánh giá lựa chọn cuối cùng ít thiên lệch hơn.

Ưu tiên tiếp theo: đối chiếu yêu cầu giảng viên, thống nhất tiêu chí chính trước thí nghiệm mới, cân bằng ngân sách tinh chỉnh, kiểm thử theo thời gian/đội xe ngoài, đối chiếu dung lượng RPT nếu có. Phân loại lỗi đã được bổ sung trên dữ liệu Zenodo 18505707 v1 có nhãn riêng: 99 xe, 47.698 mẫu. Mô hình vẫn có 87 mẫu lỗi bị bỏ sót và 281 mẫu báo nhầm trong kiểm thử; không xác nhận hỏng/an toàn tuyệt đối. Chi tiết nằm trong docs/health-and-fault.md và reports/fault/summary.json.

## 7. Dàn ý bảo vệ 8 phần

1. Bài toán: cần ước tính SOH từ tín hiệu ngắn, phân biệt SOH với SOC.
2. Dữ liệu: SDU là chính; BMS là thực nghiệm vận hành riêng, giải thích nguồn nhãn.
3. Xử lý và đặc trưng: cửa sổ 120 giây, kiểm tra chất lượng, tách nhãn.
4. Kiểm thử: chia nhóm pin/xe, 5 vòng, chống rò rỉ, tiêu chí MAE macro.
5. Kết quả: đủ mô hình, MAE/RMSE/R², chênh lệch và độ nhất quán theo nhóm.
6. Demo: pin chưa học; phân biệt với mô hình bàn giao đã học lại toàn bộ dữ liệu.
7. Đóng góp: quy trình, thực nghiệm và phần mềm; không tự nhận thuật toán mới.
8. Hạn chế và kết luận: trả lời mục tiêu SOH, không suy diễn tốt/hỏng từ dung lượng.

## 8. Câu hỏi thường gặp khi bảo vệ

**Vì sao không nói chính xác 97% khi R² khoảng 0,97?** R² là mức giải thích biến thiên so với dự đoán trung bình; không phải tỷ lệ mẫu đúng.

**Mô hình mới có hơn mô hình cũ không?** Ridge–RF chỉ hơn rất ít theo MAE macro SDU, không hơn mọi tiêu chí. BMS có mức giảm MAE khoảng 3,33% trên nhãn suy ra và 20 xe khảo sát.

**Vì sao dùng BMS nếu nhãn chưa phải đo độc lập?** Để kiểm tra khả năng khớp chỉ số dung lượng suy ra trên dữ liệu vận hành; công bố rõ giới hạn, không xem là xác nhận SOH vật lý.

**Pin còn 92% có nghĩa không hỏng không?** Không. Đó là sức khỏe dung lượng ước tính; chẩn đoán lỗi cần dữ liệu khác.

**Mô hình có học lẫn pin kiểm thử không?** Thiết kế mã nguồn và tệp fold cho thấy tách theo pin/xe; audit đã kiểm tra mẫu, nhãn và fold. Để xác nhận lịch sử huấn luyện hoàn toàn độc lập cần chạy tái lập huấn luyện.

**Đã đạt khóa luận chưa?** Kết quả có bằng chứng thực nghiệm để trình bày; việc đạt yêu cầu và chấm điểm theo tiêu chí trường và hội đồng.
