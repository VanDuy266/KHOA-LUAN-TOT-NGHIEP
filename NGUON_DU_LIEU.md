# Nguồn dữ liệu SDU 2025

## Trích dẫn bộ dữ liệu

Wang, S., Gao, F., & Tian, H. (2025). *Data for: Deep sorting of reused batteries for enabling long-term consistency grouping with unknown prior conditions* [Data set]. Zenodo. https://doi.org/10.5281/zenodo.14859405

- Trang tải của tác giả: https://zenodo.org/records/14859405
- Đơn vị của ba tác giả theo metadata: Shandong University.
- Ngày công bố dữ liệu: 12/02/2025. Đây là ngày công bố, không phải khẳng định toàn bộ phép đo được thực hiện năm 2025.
- Giấy phép: Creative Commons Attribution 4.0 International (CC BY 4.0), cần ghi công nguồn khi sử dụng.
- Bài báo liên quan theo metadata Zenodo: *Deep sorting of reused batteries for enabling long-term consistency grouping with unknown prior conditions*, Cell Reports Physical Science. https://doi.org/10.1016/j.xcrp.2025.102657

## Hai file gốc

| File | Kích thước byte | MD5 do Zenodo cung cấp |
| --- | ---: | --- |
| Primary_use_phase.zip | 2694002794 | 15d94a62d47dd9036899889b3f36992d |
| Second_life_phase.zip | 1794732202 | 0ba11864d2c1017c84d96dfe578956fc |

Hai file gốc đã tải đủ và khớp MD5; không bị ghi đè. Metadata đầy đủ nằm trong source_metadata.json.

## Dữ liệu thí nghiệm

Theo tác giả, dữ liệu thu từ 86 cell Lishen LR1865SZ, điện cực NMC(532)/graphite, dung lượng danh định 2,4 Ah. Thí nghiệm lão hóa kéo dài 30 tháng, gồm sử dụng ban đầu và tái sử dụng. Hai giai đoạn thuộc cùng 86 pin, không phải 172 pin độc lập. File được đặt tên theo số hiệu thí nghiệm ban đầu; cột Battery_ID là mã đối chiếu trong bài báo.

Đây là dữ liệu phòng thí nghiệm trên cell pin, chưa phải dữ liệu pack hoặc xe điện vận hành tại Việt Nam.

## Tập con trong gói này

1. Đọc và kiểm tra 145.112.317 dòng, 89.677 chu kỳ ghi nhận từ 172 CSV nguồn.
2. Chọn các đoạn xả ở điều kiện tham chiếu khoảng 0,2C: dòng -0,48 A, đầu xả ít nhất 4 V, cuối xả gần 3 V, cùng các kiểm tra tín hiệu và dung lượng. Kết quả: 30.929.675 dòng thuộc 20.823 chu kỳ của 86 pin. Đây là nhận diện điều kiện xả từ tín hiệu, không phải khẳng định mọi chu kỳ đều có nhãn chẩn đoán do tác giả cấp.
3. Bản 10.000.000 dòng giữ đủ 20.823 chu kỳ và 86 pin. Giữ toàn bộ mẫu 120 giây đầu xả và điểm cuối mỗi chu kỳ; giảm mật độ mẫu ở đoạn sau theo thứ tự thời gian. Đây là lấy thưa, không phải tuyên bố mọi điểm bị bỏ là nhiễu.
4. Dòng CSV được chọn giữ nguyên văn: tên cột, số đo, mã pin, số chu kỳ và thứ tự nguồn. Không nội suy, điền giá trị thiếu, nhân bản hoặc sửa số đo. Đây là tập con do dự án tạo, không phải nguyên gói tác giả phát hành.
5. Bảng đặc trưng và nhãn được tạo riêng. SOH (%) = dung lượng xả tham chiếu / 2,4 × 100. Nhãn lấy từ chu kỳ đầy đủ; không tính lại bằng đường đã lấy thưa. Các file bảng mô hình được đối chiếu với bộ đầy đủ.

Trong báo cáo có thể ghi: “Tôi sử dụng bộ dữ liệu SDU công bố năm 2025 của Wang, Gao và Tian. Tập con gồm 10 triệu dòng đo xả, giữ đủ 20.823 chu kỳ ở điều kiện tham chiếu của 86 pin. Mọi điểm đo trong 120 giây đầu được giữ để tính đặc trưng; phần sau được lấy thưa để giảm dung lượng lưu trữ.”

Chất lượng của bản được phát kèm nằm trong KET_QUA_KIEM_TRA.md và verification/. Tính toàn vẹn file không chứng minh mọi tín hiệu đều không có nhiễu.
