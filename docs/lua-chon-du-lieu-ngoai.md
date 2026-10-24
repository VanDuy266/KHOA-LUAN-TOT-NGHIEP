# Lựa chọn dữ liệu ngoài cho bài toán SOH

Khảo sát ngày 24/10/2026. Giữ nguyên SDU và mô hình hiện tại; chưa ghép dữ liệu ngoài, chưa huấn luyện lại.

## Kết luận

Chưa xác minh được bộ BMS trên xe công khai đồng thời có chuỗi điện áp tế bào/dòng điện/nhiệt độ, mốc chu kỳ và dung lượng tham chiếu để kiểm thử trực tiếp mô hình SDU. Cùng tên NMC không bảo đảm cùng phân phối dữ liệu. Không đổi điện áp bộ pin thành điện áp tế bào bằng giả định và không dùng SOH do BMS ước tính như nhãn dung lượng đo độc lập.

Nếu cần thêm một nguồn thực nghiệm SOH, ưu tiên khảo sát dữ liệu NMC LG Chem dưới đây vì đọc được tín hiệu và dung lượng từ CSV gốc. Đây là hướng nghiên cứu ngoài bộ dữ liệu chính, chưa phải kiểm chứng trên xe.

## NMC LG Chem E71A — đã kiểm tra mẫu CSV

- Nguồn: https://zenodo.org/records/19387650.
- Tên: Five ageing datasets for NMC lithium-ion pouch cells.
- Tác giả: Radostin Pavlov và Gaizka Busteros, EURECAT Centre Tecnològic de Catalunya.
- Công bố 02/04/2026; CC BY 4.0.
- Năm tập thí nghiệm tế bào LG Chem E71A, NMC, dung lượng danh định 69,5 Ah. Các phép thử 0,5C, 1C hoặc 1,44C; cứ 50 chu kỳ có ba chu kỳ kiểm tra dung lượng C/3, theo mô tả tác giả.
- Các số chu kỳ cuối tác giả công bố: 1.091, 1.088, 399, 1.539 và 319 tương ứng rc01, rc02, rc04, rc05, rc06. Chưa kiểm đếm toàn bộ file để xác nhận số chu kỳ này.
- Đã tải đúng 65.536 byte đầu `rc06_reduced.csv` bằng HTTP Range, đọc được 560 dòng hoàn chỉnh. Chưa tải toàn bộ CSV 562.576.401 byte. Mẫu có một ô nhiệt độ thiếu; chưa kiểm tra toàn bộ dữ liệu và không kết luận đã sạch.
- Cột thực tế: Time (h), Date_Time, Step Index, Cycle Number, Current (A), Voltage (V), Charge Capacity (Ah), Discharge Capacity (Ah), Temperature (ºC).
- Đủ loại tín hiệu để nghiên cứu SOH sau khi xử lý riêng. Phải kiểm tra/reset dung lượng theo bước, nhận diện chu kỳ kiểm tra, đơn vị thời gian, quy ước dòng, giá trị thiếu và cách tác giả định nghĩa SOH trước khi tạo nhãn.
- Không chạy trực tiếp bằng mô hình SDU: khác dung lượng, dòng xả, quy trình và cấu trúc file. Cần thiết kế chuẩn hóa theo dung lượng/dòng C-rate, huấn luyện hoặc kiểm thử chuyển miền riêng và giữ riêng tế bào đánh giá. Chỉ năm tập nên không kỳ vọng bằng chứng tổng quát hóa rộng.
- Các thí nghiệm dừng khi quan sát phồng pin quá mức; không mặc định mọi pin đã đạt SOH 80% và không tự gán nhãn RUL.
- Bằng chứng kiểm tra mẫu: `reports/external_nmc_source_check.json`.

## KIT NMC/C+SiO năm 2024 — nguồn có triển vọng, chưa đọc mẫu tín hiệu

- Bài báo dữ liệu: https://doi.org/10.1038/s41597-024-03831-x.
- Log: https://zenodo.org/records/14555843; kết quả dung lượng/trở kháng: https://zenodo.org/records/14555851; CC BY 4.0.
- Mô tả tác giả: 228 tế bào, gần 600 ngày lão hóa, có chu trình lái xe và kiểm tra dung lượng. Đây vẫn là thí nghiệm phòng lab, không phải BMS trên xe.
- File Zenodo chỉ là Readme.txt dẫn đến kho KIT. Môi trường hiện tại bị proxy trả 403 khi truy cập radar.kit.edu, kể cả lần thử ngoài sandbox. Chưa tải log/kết quả thực và chưa kiểm tra tương thích.
- Nguồn log: https://radar.kit.edu/radar/en/dataset/kww7jv8ajuvchcah.
- Nguồn kết quả: https://radar.kit.edu/radar/en/dataset/CoNQplSNoVeXExyV.

## BMS ngoài thực tế LFP năm 2024

https://zenodo.org/records/13715694 có tín hiệu BMS ở cấp tế bào, nhưng khác hóa học/dung lượng và chưa rõ từng hệ thống có dùng trên xe hay không. Chỉ phù hợp khảo sát giám sát tín hiệu hoặc phát hiện bất thường bằng phương pháp riêng sau khi kiểm tra, không là bằng chứng mô hình SOH SDU đã dùng được trên xe.

## Phương án cho khóa luận

1. Giữ SDU làm thực nghiệm chính, đánh giá giữ riêng mã pin như hiện tại.
2. Nếu mở rộng SOH ngoài nguồn: tiếp tục kiểm tra đầy đủ một file LG Chem trước, chỉ xây bộ chuyển đổi sau khi xác minh chu kỳ kiểm tra và nhãn dung lượng. Không trộn ngẫu nhiên với SDU.
3. Nếu yêu cầu bắt buộc kiểm chứng trên xe: cần dữ liệu xe có đủ tín hiệu và dung lượng đo đối chiếu hoặc hợp tác thu thập. Các nguồn đã khảo sát chưa đáp ứng trọn điều kiện này.
