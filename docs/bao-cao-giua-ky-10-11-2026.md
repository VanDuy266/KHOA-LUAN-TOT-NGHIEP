# BÁO CÁO GIỮA KỲ KHÓA LUẬN TỐT NGHIỆP

Ngày báo cáo: 10/11/2026. Bản tiến độ cập nhật từ kết quả thực nghiệm đã lưu, không phải xác nhận nghiệm thu cuối kỳ.

Đề tài: Phân tích và dự đoán tình trạng sức khỏe pin xe điện bằng các mô hình học máy.

Sinh viên: Nguyễn Văn Duy — MSSV 2311553949 — Chuyên ngành Khoa Học Dữ Liệu.

## 1. Mục tiêu và phạm vi

Phân tích dữ liệu điện áp, dòng điện, nhiệt độ và dung lượng; dự đoán SOH từ đầu chu kỳ xả; so sánh mô hình trên pin chưa được học; xây dựng ứng dụng Vincent D. Dữ liệu thực nghiệm ở cấp tế bào trong phòng thí nghiệm. Chưa kiểm chứng trên BMS xe thực tế và chưa triển khai RUL; hai nội dung này không được ghi là chức năng đã hoàn thành.

## 2. Dữ liệu đã triển khai

SDU 2025: 86 pin Lishen 2,4 Ah, hai giai đoạn thuộc cùng các pin; 10.505.065 điểm đo được giữ, 20.823 chu kỳ xả tham chiếu. Nguồn Zenodo 14859405, CC BY 4.0.

XJTU 2024: chọn 23/55 pin Lishen NCM 2 Ah thuộc Batch-1/2 vì quy trình cố định. Đã tải 23 MAT nguyên gốc, kiểm CRC/SHA, trích xuất từ 46,215,511 điểm đo. Có 6,961 chu kỳ đạt kiểm tra đầu vào; 6,938 chu kỳ sau khi không dùng 23 chu kỳ đo đầu 0,2C cho đánh giá xả 1C. Nguồn Zenodo 10963339, CC BY 4.0.

Giữ nguyên nguồn. Không ghép hai bộ như một tập đồng nhất và không sửa số dòng để làm đẹp quy mô. Dung lượng danh định và dòng xả khác nhau, nên dùng quy trình riêng và báo cáo chuyển miền riêng.

## 3. Quy trình xử lý và đánh giá

Nguồn → kiểm tra cấu trúc/dung lượng → tách chu kỳ xả → cửa sổ 120 giây → đặc trưng hoặc chuỗi → giữ riêng mã pin → huấn luyện → dự đoán pin kiểm thử → MAE/RMSE/R² → ứng dụng.

SDU dùng 12 đặc trưng. XJTU dùng 11 đặc trưng chung: bỏ phase_code, chia dòng điện cho dung lượng danh định. Dung lượng đo cả chu kỳ chỉ tạo nhãn SOH, không làm đầu vào. GRU dùng 25 vị trí V/I/T và biến ngữ cảnh; chuẩn hóa chỉ học từ train.

Chia 5 vòng theo pin vật lý, seed 42; không chia ngẫu nhiên các điểm cảm biến của cùng pin vào hai tập. MAE/RMSE tính theo điểm phần trăm SOH, kết quả chính lấy trung bình theo pin. R² có thể âm khi mô hình chuyển miền kém.

## 4. Kết quả SDU

| model | mae | rmse | r2 |
| --- | --- | --- | --- |
| Mean baseline | 13.246 | 15.249 | -0.281 |
| Ridge | 2.582 | 3.299 | 0.933 |
| Random Forest | 1.619 | 2.157 | 0.970 |
| LightGBM | 1.734 | 2.270 | 0.968 |
| GRU | 2.141 | 2.718 | 0.953 |

Random Forest là cấu hình demo SDU cố định: MAE 1.619, RMSE 2.157, R² 0.970. Điểm này thuộc kiểm thử pin giữ riêng; artifact ứng dụng sau đó refit trên toàn bộ dữ liệu, không dùng điểm refit thay điểm kiểm thử.

## 5. Kết quả bổ sung XJTU

| model | mae | rmse | r2 |
| --- | --- | --- | --- |
| Mean baseline | 3.759 | 4.720 | -0.057 |
| Ridge | 0.971 | 1.205 | 0.920 |
| Random Forest | 0.577 | 0.764 | 0.965 |
| LightGBM | 0.596 | 0.787 | 0.964 |
| Ridge-RF residual | 0.666 | 0.828 | 0.960 |
| RF multi-source | 0.623 | 0.867 | 0.945 |
| GRU | 1.240 | 1.543 | 0.856 |

RF đa nguồn học từ SDU và các pin XJTU thuộc train của từng vòng, cân bằng tổng trọng số hai nguồn; không học nhãn pin XJTU đang kiểm tra. So sánh cần xem cả MAE và RMSE; thêm dữ liệu không bảo đảm sai số giảm.

Kết quả chuyển miền và giữ riêng batch được trình bày riêng:

| design | model | mae | rmse | r2 |
| --- | --- | --- | --- | --- |
| SDU to XJTU | RF normalized | 42.654 | 42.910 | -89.595 |
| SDU to XJTU | RF original SDU | 12.836 | 13.649 | -8.045 |
| Held-out batch 1 | Random Forest | 1.237 | 1.604 | 0.890 |
| Held-out batch 2 | Random Forest | 3.352 | 4.420 | -0.354 |

Không suy rộng kết quả này thành dự đoán chính xác mọi loại pin xe điện. Đây là thực nghiệm ban đầu trên cấu hình cố định; chưa có đánh giá đa seed hoặc kiểm chứng xe.

## 6. Sản phẩm hiện có

Vincent D có tra cứu pin, biểu đồ, so sánh mô hình, dự đoán một/lô SDU, lịch sử, kiểm tra chất lượng, phát hiện xu hướng SOH bất thường và xuất CSV. Mục XJTU tách riêng kết quả kiểm thử, nguồn, dự đoán MAT bằng RF riêng hoặc đa nguồn. Các cờ bất thường chỉ yêu cầu xem xét, chưa là chẩn đoán hỏng pin.

Mã nguồn, bảng kết quả, notebook, báo cáo và slide được lưu trên GitHub. Dữ liệu gốc lớn được tải từ nguồn bằng script, không cần đưa toàn bộ vào RAM để chạy giao diện. Các notebook đã có đầu ra để xem riêng mà không mở Streamlit.

## 7. Nội dung đã làm và phần cần tiếp tục

Đã triển khai: dữ liệu chính SDU, kiểm thử mô hình theo pin, mô hình Ridge–RF phần dư, giám sát xu hướng, ứng dụng; mở rộng XJTU Batch-1/2, kiểm thử độc lập theo pin, kiểm tra chuyển miền và RF đa nguồn.

Cần tiếp tục trước nghiệm thu cuối kỳ: rà soát diễn giải sai số theo pin/điều kiện, kiểm tra tính ổn định cấu hình, đối chiếu báo cáo và mã nguồn; chỉnh định dạng theo mẫu trường và nhận xét giảng viên. BMS trên xe và RUL là giới hạn/hướng mở rộng, không tự động đưa vào phạm vi bắt buộc.

## 8. Kế hoạch chuẩn bị ngày 10/11/2026

| Thời gian | Công việc |
| --- | --- |
| 25–29/10 | Rà soát nguồn, nhãn và phân hoạch; kiểm tra mã và chạy sản phẩm trên máy cá nhân |
| 30/10–03/11 | Phân tích sai số, đối chiếu bảng/biểu đồ và hoàn thiện báo cáo tiến độ |
| 04–07/11 | Chốt slide, lựa chọn ví dụ demo và bản dự phòng kết quả |
| 08–09/11 | Tập trình bày, chuẩn bị trả lời câu hỏi về SOH, chia dữ liệu và giới hạn |
| 10/11 | Báo cáo giữa kỳ và ghi nhận góp ý |

Lịch trên là kế hoạch chuẩn bị đề xuất; điều chỉnh theo lịch và mẫu giảng viên cung cấp.

## 9. Tài liệu trình chiếu và bàn giao giữa kỳ

Slide: docs/slide-giua-ky-10-11-2026.pptx. Báo cáo tiến độ: docs/bao-cao-giua-ky-10-11-2026.docx. Notebook: 01_eda, 02_ket_qua_tung_phan và 03_thuc_nghiem_xjtu. Thực nghiệm lưu ở reports và reports/xjtu. Demo chạy bằng chay_windows.ps1 từ thư mục gốc. Hồ sơ cuối kỳ vẫn theo yêu cầu chính thức của trường.
