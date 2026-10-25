# Kết quả kiểm chứng phục vụ khóa luận

## Phạm vi và cách tính

Đây là kiểm tra lại dự đoán ngoài tập huấn luyện đã lưu, không phải một lượt huấn luyện lại. Mỗi pin/xe chỉ thuộc một vòng kiểm thử; toàn bộ mẫu của cùng pin/xe được giữ cùng nhóm. SDU có 20,823 chu kỳ từ 86 pin; BMS có 27,205 phiên từ 20 xe. Cả hai dùng 5 vòng kiểm thử theo nhóm.

MAE và RMSE có đơn vị điểm phần trăm SOH: dự đoán 90 khi tham chiếu 92 là sai lệch 2 điểm %. R² không phải độ chính xác phân loại và không được đổi thành phần trăm pin tốt/hỏng. Bảng chính là trung bình chỉ số tính riêng trên mỗi pin/xe (macro); CSV cũng cung cấp chỉ số gộp tất cả mẫu (pooled), không trộn hai cách tính.

## SDU: dự đoán SOH trên pin giữ riêng

| Mô hình | MAE (điểm %) | RMSE (điểm %) | R² |
|---|---:|---:|---:|
| Ridge-RF residual | 1.6122 | 2.1599 | 0.9708 |
| Random Forest | 1.6189 | 2.1572 | 0.9705 |
| CatBoost | 1.6773 | 2.1880 | 0.9696 |
| XGBoost | 1.6924 | 2.2121 | 0.9692 |
| LightGBM | 1.7344 | 2.2700 | 0.9677 |
| GRU | 2.1414 | 2.7180 | 0.9528 |
| Ridge | 2.5818 | 3.2986 | 0.9332 |
| Mean baseline | 13.2459 | 15.2489 | -0.2809 |

Mô hình có MAE macro thấp nhất trong các cấu hình đã thử là Ridge-RF residual: MAE 1.6122, RMSE 2.1599 điểm % và R² 0.9708. Kết quả này không phải xác suất dự đoán đúng của một pin cụ thể.

Ridge–RF so với Random Forest có chênh MAE trung bình -0.006713 điểm %, cải thiện trên 40/86 pin. Khoảng bootstrap mô tả 95% cho chênh trung bình là [-0.047043; 0.030363]. Không tuyên bố ưu thế chắc chắn khi khoảng chứa 0; cũng không khẳng định thuật toán mới hay tốt nhất phổ quát. Khoảng này không điều chỉnh phụ thuộc do tập huấn luyện CV dùng chung hoặc việc thử nhiều mô hình.

CatBoost/XGBoost có chọn siêu tham số bằng nhóm validation bên trong tập học; các baseline dùng cấu hình cố định, nên ngân sách tinh chỉnh chưa ngang nhau. GRU dùng biểu diễn chuỗi khác mô hình bảng; khác biệt không chỉ nằm ở thuật toán. Mô hình bàn giao học lại toàn bộ dữ liệu không dùng để tính bảng kiểm thử này.

## BMS: dự đoán trên xe giữ riêng

| Mô hình | MAE (điểm %) | RMSE (điểm %) | R² |
|---|---:|---:|---:|
| Ridge-RF residual | 2.0998 | 2.7292 | 0.5043 |
| Random Forest | 2.1720 | 2.8316 | 0.4674 |
| Ridge | 2.8054 | 3.4162 | 0.2221 |
| Mean baseline | 3.3205 | 3.9777 | -0.0418 |

Ridge-RF residual có MAE macro thấp nhất: 2.0998 điểm %. SOH tham chiếu BMS được suy ra từ tích phân dòng điện và độ tăng SOC ở phần sau cửa sổ đầu sạc, tổng hợp theo xe–tháng. Đây là đánh giá độ khớp với nhãn suy ra, chưa phải xác nhận độ chai bằng phép đo dung lượng độc lập. Nhiều phiên cùng xe–tháng dùng chung nhãn, không được xem là các phép đo dung lượng độc lập. Không so trực tiếp MAE SDU với BMS để kết luận mô hình nào tốt hơn.

## Kiểm tra chống rò rỉ và giới hạn bằng chứng

Đã kiểm tra đủ mẫu, không lặp mẫu trong mỗi mô hình, nhãn tham chiếu khớp nguồn, đúng fold vật lý và bộ fit/validation/test boosting không giao nhau. Đặc trưng khai báo không chứa nhãn dung lượng, SOH hay mã pin/xe. Mã huấn luyện cho thấy scaler được fit trong tập học. Đây là kiểm tra tệp dự đoán và mã nguồn; chưa phải tái huấn luyện độc lập để chứng minh toàn bộ lịch sử thực thi. Hash của đầu vào và mã nằm trong verification.json.

Kiểm thử giữ riêng pin/xe đánh giá chuyển sang đối tượng khác, không chứng minh dự đoán tương lai theo thời gian. Tập kiểm thử đã được xem khi so sánh mô hình; nếu cần ước lượng không thiên lệch cho lựa chọn cuối cùng, cần một tập ngoài chưa dùng lựa chọn hoặc nested CV cho toàn bộ quy trình chọn mô hình.

## Đóng góp và cách trình bày khi bảo vệ

Đóng góp của đề tài là xây dựng quy trình trích xuất tín hiệu đầu sạc, so sánh mô hình trên cùng nhóm pin giữ riêng, triển khai giao diện dự đoán và bổ sung kiểm chứng trên dữ liệu vận hành xe riêng biệt. Không gọi phối hợp Ridge–RF là thuật toán mới phát minh. Không quy đổi kết quả thành phần trăm hoàn thành hay điểm khóa luận.

Có thể trình bày: “Trong các cấu hình đã khảo sát, Ridge-RF residual có MAE macro thấp nhất trên 86 pin SDU theo kiểm thử nhóm 5 vòng. BMS được đánh giá riêng trên 20 xe, với nhãn SOH suy ra từ vận hành; chưa mở rộng kết luận sang chẩn đoán pin hỏng hoặc xác nhận an toàn.”

## Phần cần hoàn thiện tiếp

Đối chiếu tiêu chí và biểu mẫu báo cáo của trường với giảng viên; bổ sung phép đo dung lượng độc lập nếu muốn xác nhận SOH BMS vật lý; dùng dữ liệu lỗi đã xác minh nếu mở rộng sang chẩn đoán hỏng. Chưa cần bổ sung nhãn tốt/hỏng cho mục tiêu hồi quy SOH hiện tại.

Chạy lại: `.venv/Scripts/python.exe scripts/audit_thesis_results.py`. Đầu ra nằm tại reports/thesis_audit; CSV giữ đầy đủ số lẻ, bảng Markdown làm tròn 4 chữ số.
