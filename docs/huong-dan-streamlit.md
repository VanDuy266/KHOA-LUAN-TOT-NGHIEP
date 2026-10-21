# Sử dụng ứng dụng Streamlit

Chạy từ thư mục dự án trên Windows:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py
```

## Các màn hình

- **Tổng quan**: chọn giai đoạn và pin để xem SOH, tải thống kê CSV.
- **Tra cứu pin**: lọc chu kỳ, xem tín hiệu và so sánh pin.
- **Đánh giá mô hình**: kết quả kiểm thử theo nhóm pin, so sánh với mốc cơ sở.
- **Dự đoán SOH**: tải CSV/CSV.GZ hoặc chọn mẫu; dự đoán một chu kỳ hay theo lô. Với file tải lên, mở **Kiểm tra file trước khi dự đoán** để xem lỗi từng nhóm pin/giai đoạn/chu kỳ. Kiểm tra không ghi lịch sử.
- **Lịch sử dự đoán**: chọn phiên hiện tại hoặc kho trên máy; lọc theo trạng thái, mã pin/tên nguồn, giai đoạn, ngày; xuất CSV hoặc phiếu HTML có thể in thành PDF từ trình duyệt.
- **Chất lượng dữ liệu**: số liệu làm sạch, các kiểm tra và định nghĩa đặc trưng.
- **Thông tin**: tác giả, tài liệu, nguồn dữ liệu, phạm vi nghiên cứu.
- **Demo pin giữ riêng**: mô hình riêng không học SDU_01 ở cả hai giai đoạn; so sánh thực tế và dự đoán, giải thích đóng góp từng đặc trưng.

Kết quả dự đoán theo lô có SOH trung bình, SOH thấp nhất, số chu kỳ ngoài miền huấn luyện và bộ lọc dưới ngưỡng SOH tùy chọn. Ngưỡng chỉ dùng để rà soát kết quả nghiên cứu, không xác nhận an toàn pin.

## Lưu kết quả lâu dài

Màn hình **Kiểm tra file đầu vào** kiểm tra riêng cấu trúc cột, giá trị thiếu/không phải số/vô hạn, định danh nhóm và cửa sổ xả từng chu kỳ. Có mẫu CSV, bảng xem trước 100 dòng và tải hai báo cáo CSV. Kiểm tra này không gọi mô hình. Các dòng sai mã pin, chu kỳ hoặc giai đoạn được báo riêng và phải sửa trước khi dự đoán.

Lịch sử hỗ trợ sắp xếp theo thời gian hoặc SOH, phân trang 25/50/100 dòng. CSV và HTML xuất toàn bộ kết quả khớp bộ lọc, không chỉ trang đang xem.

Trước khi bấm dự đoán, chọn **Lưu kết quả vào kho trên máy này**. Mặc định tắt. Kho SQLite tại `data/local/prediction_history.sqlite3` lưu kết quả, tên nguồn và thời gian, không lưu nội dung file đầu vào. Yêu cầu trùng mã được ghi một lần. Kho dùng chung cho người truy cập cùng máy chủ; không phải lịch sử riêng theo tài khoản. Chỉ dùng trên máy cá nhân hoặc môi trường được kiểm soát nếu dữ liệu cần giữ riêng.

Lịch sử phiên giữ tối đa 500 chu kỳ; thao tác xóa lịch sử phiên không xóa kho lâu dài. Thư mục `data/local/` được loại khỏi Git. Sao lưu file SQLite khi ứng dụng đã dừng nếu muốn chuyển máy; không xóa file kho khi cập nhật mã nguồn.

## Tạo lại mô hình demo

```powershell
.\.venv\Scripts\python.exe scripts/build_demo_model.py
```

Chạy lại sau khi cập nhật bảng `reports/features.csv`. Mô hình demo là `artifacts/random_forest_demo.joblib`, tách biệt mô hình sản phẩm. Trang demo kiểm tra mã băm bảng dữ liệu trước khi sử dụng. Demo minh họa một pin, không thay thế kết quả kiểm thử 5 vòng.

Phần giải thích phân rã dự đoán theo đường đi trong cây; mốc cộng tổng đóng góp bằng dự đoán. Không diễn giải đóng góp thành nguyên nhân vật lý hoặc xác suất chính xác.

## Kiểm tra tính năng mới

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_demo.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_history_store.py -v
```
