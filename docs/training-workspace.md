# Huấn luyện thử và so sánh mô hình

## Hai loại kết quả được tách riêng
Bảng So sánh mô hình dùng kết quả kiểm thử 5 vòng đã audit của SDU và BAIC. Các tệp nhãn và dự đoán chính không thay đổi khi người dùng huấn luyện thử.

Huấn luyện thử nhận CSV đặc trưng có nhãn SOH, 40–5.000 dòng, 4–200 mã pin, mỗi pin ít nhất 5 mẫu. Không nhận file tín hiệu thô để tự suy nhãn. Có CSV mẫu từ một tập con SDU để kiểm tra định dạng; kết quả trên tập con này không thay thế kết quả 86 pin.

## Phương pháp thử cố định
Giữ riêng 25% mã pin bằng GroupShuffleSplit, seed 42. Hai giai đoạn của cùng pin ở cùng phía. Nhãn SOH, mã pin và cột ngoài danh sách đặc trưng không được đưa vào mô hình. Chuẩn hóa Ridge chỉ fit trên train. Không tinh chỉnh theo test.

Mốc trung bình dùng nhãn train. Ridge alpha=1, StandardScaler. Random Forest 80 cây, max_depth=10, min_samples_leaf=3, một luồng, seed42. Cấu hình bị giới hạn để không làm máy chủ miễn phí quá tải; không chạy nền hay giả phần trăm tiến trình. Nếu mô hình đang bận, yêu cầu huấn luyện trả mã 429 và không khởi chạy thêm.

MAE/RMSE được tính theo từng pin test rồi lấy trung bình đều. R² chỉ tính khi nhãn pin đó có biến thiên; bỏ trống khi không xác định. Biểu đồ chọn đúng pin/giai đoạn để không nối sai lịch sử.

## Tải và tái lập
Gói ZIP gồm ba model joblib do máy chủ tạo, results.json, held_out_predictions.csv. Metadata ghi mã pin train/test, đặc trưng, nguồn nhãn người dùng khai báo, SHA256 CSV, cấu hình và phiên bản thư viện. Mô hình thử không thay artifact đang phục vụ và không tự thêm vào lựa chọn dự đoán chính.

Một lần holdout không bảo đảm tổng quát hóa, không phải chứng nhận chất lượng trên nguồn mới. Người dùng phải có nhãn tham chiếu đáng tin cậy; phần mềm không xác minh độ đúng của nhãn chỉ bằng định dạng CSV. SOH không xác nhận pin hỏng/an toàn.
