# Rà soát phạm vi và kết quả bàn giao

## Phạm vi web đã chốt
Đề tài: Phân tích và dự đoán tình trạng sức khỏe pin xe điện bằng các mô hình học máy.

Năm mục chức năng và mục Thông tin đề tài: Tổng quan; Phân tích pin; Xu hướng dung lượng; Dấu hiệu lỗi; Huấn luyện & so sánh mô hình; Thông tin đề tài. Mục thông tin giữ tác giả, đơn vị, nguồn dữ liệu, phương pháp và phạm vi. Dữ liệu bên ngoài, tính từ dung lượng đo và các mô hình SDU/BAIC là bước bên trong Phân tích pin. Demo pin giữ riêng là bước bên trong So sánh mô hình. Không còn menu SHAP/ICA/NASA, chế độ bảo vệ riêng, lịch sử riêng, tra cứu riêng hay bảng chất lượng dữ liệu riêng. Tài liệu và mã thực nghiệm được giữ để bàn giao và kiểm chứng.

## Kết quả cuối cùng của ứng dụng
- SOH, mức chai và dung lượng còn lại ước tính khi đầu vào thuộc phạm vi mô hình hỗ trợ.
- Dự báo đến mốc dung lượng từ lịch sử, có điều kiện từ chối ngoại suy.
- Dấu hiệu lỗi từ điện áp từng cell bằng mô hình riêng; đối chiếu nhãn nguồn khi có.
- MAE/RMSE/R² và thời gian thực nghiệm, trên cùng nhóm kiểm thử trong từng nguồn.
- Nhận CSV/CSV.GZ tối đa 512 MiB qua bộ tiếp nhận đọc từng khối; lọc pin/chu kỳ/giai đoạn, giữ tối đa 100.000 dòng. JSON tối đa 20 MiB. Đây không phải hỗ trợ mọi định dạng hay mọi loại pin.

## Lỗi và điểm gây hiểu nhầm đã xử lý
1. Giới hạn 20 MiB cản file nhiều chu kỳ: thêm bộ đọc CSV từng khối, giới hạn tài nguyên rõ ràng và bộ lọc nhóm, không nạp cả CSV vào RAM.
2. Mất mã pin/chu kỳ/giai đoạn sau chuẩn hóa: giữ lại trường hợp lệ trong CSV chuyển sang mô hình; tránh dùng nhầm chu kỳ 1 hoặc giai đoạn mặc định.
3. Điều hướng nhiều trang rời gây rối: còn năm mục chức năng cùng Thông tin đề tài và chuyển link cũ về mục phù hợp. Đổi tên hàm history cũ để tránh che History API của trình duyệt.
4. Đầu ra mô hình ngoại suy quá xa SOH: endpoint dự đoán không xuất kết quả thành công ngoài miền hỗ trợ 0–130%; không cắt số để che sai số trong báo cáo nghiên cứu NASA.
5. Trộn số liệu kiểm chứng với kết quả một mẫu: thu gọn chỉ số vào chi tiết; không gọi recall 97% là độ chắc chắn của một mẫu.
6. SOH/SOC/điện lượng đoạn đo: tách ý nghĩa; không suy SOH hay dung lượng đầy từ đoạn sạc/xả không đầy đủ.

## Rò rỉ và phạm vi kiểm chứng
Audit tệp OOF và mã nguồn xác nhận cùng nhóm pin/xe không chia sang cả train/test, nhãn nguồn khớp, phủ mẫu, không trùng và chỉ số tính lại khớp. Đây không phải tái huấn luyện độc lập toàn bộ mô hình.

BMS dùng nhãn suy ra và tổng hợp theo xe–tháng; có thể dùng thông tin muộn trong tháng nên là kiểm chứng hồi cứu, không chứng minh dự đoán tương lai thời gian thực. Test đã được xem để so sánh mô hình; cần nguồn ngoài chưa dùng lựa chọn nếu muốn kết luận ít thiên lệch hơn. SHAP tổng hợp mô tả mô hình cuối có mẫu tham gia học, không dùng làm độ chính xác ngoài tập học. Không khẳng định không rò rỉ 100%.

## Thành quả và giới hạn
SDU: Ridge–RF MAE macro 1,6122 điểm % so với RF 1,6189; cải thiện nhỏ, khoảng chênh có chứa 0. BAIC: Ridge–RF MAE macro 2,0998 so với RF 2,1720, giảm khoảng 3,33% sai số trong tập xe đã thử. Không gọi đây là độ chính xác 98%.

NASA: 636 chu kỳ ngoài nguồn cho thấy chuyển thẳng mô hình SDU kém; mô hình gộp chưa hơn NASA riêng. Kết quả âm được giữ làm bằng chứng giới hạn tổng quát hóa. Chưa làm MIT. Không khẳng định pin an toàn hoặc không hỏng từ SOH. Không suy nhãn lỗi của bộ 99 xe sang BAIC.

Kiểm tra thực hiện: audit_thesis_results.py; bộ pytest tests; kiểm tra trình duyệt toàn bộ năm mục, lọc file nhiều nhóm, chuyển ngữ cảnh, demo, kết quả và giao diện điện thoại. Tệp này không thay kết luận đánh giá của giảng viên.


## Cập nhật giao diện và huấn luyện thử
Khung đề tài nổi bật, thống nhất màu sắc và kiểu chữ Times New Roman; giữ hiệu ứng avatar. Bảng so sánh chọn riêng SDU/BAIC, đổi chỉ số MAE/RMSE/R² và hiển thị mức chênh so với Random Forest. Dữ liệu so sánh được tổng hợp từ kết quả đã audit, có kiểm tra hash nguồn khi build để tránh hiển thị cũ. Thời gian chưa có số đo được để trống.

Bổ sung huấn luyện thử trên CSV đặc trưng có nhãn với chia nhóm pin 25% giữ riêng, StandardScaler chỉ fit train, cấu hình Mean/Ridge/RF cố định và giới hạn dữ liệu. Tải ZIP chứa mô hình, cấu hình/phiên bản, SHA256, nguồn nhãn và dự đoán test. Chức năng này không cập nhật artifact chính hoặc nhập kết quả thử vào bảng chính. CSV mẫu chỉ là tập con để thử thao tác. Không khẳng định sản phẩm chính xác 100% cho mọi loại pin.
