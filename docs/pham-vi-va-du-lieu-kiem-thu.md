# Phạm vi nghiên cứu và dữ liệu kiểm thử bổ sung

## Phạm vi chính

Khóa luận phân tích và dự đoán SOH ở cấp tế bào pin lithium-ion, thực nghiệm trên dữ liệu SDU công bố năm 2025. Dữ liệu gồm 86 tế bào Lishen LR1865SZ, hóa học NMC(532)/graphite, dung lượng danh định 2,4 Ah, trong giai đoạn sử dụng ban đầu và tái sử dụng. Hai giai đoạn thuộc cùng các tế bào, không phải 172 pin độc lập.

Tập được chọn có 10.505.065 điểm đo và 20.823 chu kỳ xả tham chiếu. Mô hình học từ 12 đặc trưng của 120 giây đầu chu kỳ xả. SOH tham chiếu được tính bằng dung lượng xả toàn chu kỳ chia dung lượng danh định, nhân 100%. Kiểm thử giữ riêng mã pin giữa các tập để đánh giá trên pin chưa được học.

Kết quả hiện tại phản ánh điều kiện thí nghiệm SDU. Chưa chứng minh mô hình dùng được trực tiếp trên bộ pin xe thương mại, hóa học khác, dung lượng khác hoặc điều kiện vận hành tại Việt Nam. Điện áp toàn bộ pin không thay thế điện áp tế bào. Chưa có phép đo BMS do nhóm thu thập trên xe và chưa có kiểm chứng dự đoán SOH trên xe thực tế.

Phát hiện xu hướng bất thường dùng lịch sử SOH tham chiếu đã đo để đánh dấu chu kỳ cần xem xét. Chưa có nhãn lỗi được xác nhận để đánh giá khả năng chẩn đoán hư hỏng; cờ bất thường không phải kết luận pin nguy hiểm.

## RUL khác SOH

SOH là sức khỏe tại thời điểm/chu kỳ được quan sát. RUL là số chu kỳ hoặc thời gian còn lại trước một ngưỡng kết thúc sử dụng đã định nghĩa. Ngưỡng 80% có thể dùng cho một thiết kế thực nghiệm, nhưng không phải tiêu chuẩn áp dụng cho mọi pin và mọi giai đoạn tái sử dụng.

Chưa triển khai mô hình RUL. Muốn đánh giá RUL cần xác định ngưỡng phù hợp từng giai đoạn, kiểm tra pin nào thực sự đi qua ngưỡng, xử lý pin chưa quan sát tới ngưỡng và giữ riêng pin khi kiểm thử. Không thể đổi trực tiếp một giá trị SOH thành số chu kỳ còn lại.

## Kết quả tìm và kiểm tra nguồn ngoài ngày 24/10/2026

### Dữ liệu SOH xe thực tế: đã tải và kiểm tra bảng gốc

- Nguồn: https://zenodo.org/records/22643868, công bố 07/09/2026, giấy phép CC BY 4.0.
- Tên: Dataset for the article Degradation analysis of traction batteries of used electric vehicles in Czechia, Slovakia and Poland.
- File nguyên gốc: `Data SO BEV,PHEV.xlsx`, 270.860 byte; MD5 trùng mã nguồn công bố `31c2d8917e5fe14436cfb930bce6d521`.
- Có 3.171 dòng dữ liệu, 15 cột: 2.742 bản ghi BEV và 429 PHEV. Không mặc định đây là 3.171 xe độc lập vì bảng không có mã xe để kiểm tra.
- Ngày kiểm tra trong bảng: 12/07/2024–04/03/2026. Các trường gồm SOH Aviloo, SOH BMS, số km, tuổi xe và nhóm dung lượng.
- Có một bản ghi BMS_SoH = 999999, không sử dụng như phần trăm SOH. Với 3.170 cặp SOH trong khoảng kiểm tra 0–120%, chênh lệch tuyệt đối trung bình BMS–Aviloo là 2,098 điểm phần trăm; RMSE là 2,893 điểm phần trăm. Đây là sự khác biệt giữa hai nguồn SOH, không phải sai số mô hình của khóa luận và không chứng minh Aviloo là dung lượng đo độc lập.
- Không có chuỗi V/I/T, chu kỳ và cửa sổ xả để tạo 12 đặc trưng. Vì vậy không thể dùng bảng này kiểm thử trực tiếp mô hình SDU hoặc tính RUL.
- Script kiểm tra: `scripts/check_external_bms.py`; kết quả: `reports/external_bms_check.json`. Dữ liệu nguồn được giữ nguyên ngoài tập huấn luyện SDU.

### Dữ liệu BMS ngoài thực tế năm 2024: đã kiểm tra mô tả và README

- Nguồn: https://zenodo.org/records/13715694, công bố 14/09/2024, CC BY-NC 4.0.
- 28 hệ thống pin LFP khoảng 160 Ah, 8 tế bào nối tiếp mỗi hệ thống, có dòng điện, điện áp tế bào và nhiệt độ. ZIP nguồn khoảng 1,67 GB; tổng số dòng khoảng 133 triệu theo mô tả tác giả. Chưa tải và kiểm tra toàn bộ ZIP.
- Các hệ thống được khách hàng trả về nhà sản xuất vì hoạt động không đạt mong đợi. Đây là mẫu có thiên lệch, không đại diện toàn bộ pin đang vận hành.
- Ứng dụng cụ thể của từng hệ thống không được biết; không gọi đây là dữ liệu BMS đo trên xe điện đã được xác nhận.
- Có thể nghiên cứu giám sát tín hiệu, mất cân bằng điện áp và xu hướng bất thường bằng phương pháp riêng. Hóa học và dung lượng khác SDU; chưa đủ căn cứ kiểm chứng trực tiếp mô hình SOH SDU.

### Dữ liệu Renault Zoe

Nguồn https://zenodo.org/records/7033914, CC BY 4.0, công bố năm 2022, đo từ 2019 đến 2021. Đã tải ZIP 121.408.300 byte, MD5 khớp nguồn `f71321e3cc74c6f4e0a2efde689babc9`. Danh mục ZIP có hai CSV, trong đó file lớn khoảng 2,20 GB khi giải nén; chưa đọc toàn bộ nội dung vì kiểu nén không được thư viện ZIP Python hiện tại hỗ trợ. Mô tả có SOC, tốc độ, năng lượng và công suất; không liệt kê đủ điện áp tế bào, dòng điện, nhiệt độ, dung lượng tham chiếu để kiểm chứng mô hình SDU. Không nhầm SOC với SOH.

## Kết luận sử dụng

Giữ SDU làm dữ liệu chính. Bảng xe thực tế được dùng để khảo sát sự khác nhau giữa SOH BMS và hệ thống chẩn đoán, không ghép vào dữ liệu huấn luyện. Kiểm chứng trên xe và RUL vẫn là phần chưa hoàn thành; không công bố hai phần này đã đạt chỉ vì tìm được nguồn tải dữ liệu.
