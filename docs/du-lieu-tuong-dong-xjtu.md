# Dữ liệu tương đồng với SDU: XJTU Battery Dataset

## Lựa chọn

Trong các nguồn đã khảo sát, XJTU là ứng viên gần SDU hơn bộ LG Chem 69,5 Ah hoặc BMS LFP 160 Ah. Ưu tiên XJTU cho khảo sát và thực nghiệm SOH ngoài nguồn; chưa thay SDU, chưa trộn hai bộ và chưa chạy mô hình trên XJTU.

Nguồn gốc: https://zenodo.org/records/10963339 (DOI 10.5281/zenodo.10963339), công bố 12/04/2024, giấy phép CC BY 4.0. Tác giả bộ dữ liệu: Fujin Wang, Xi'an Jiaotong University. Bài báo: Wang, F., Zhai, Z., Zhao, Z. et al. Physics-informed neural network for lithium-ion battery degradation stable modeling and prognosis. Nature Communications 15, 4332 (2024). https://doi.org/10.1038/s41467-024-48779-z.

## So sánh điều kiện

| Thuộc tính | SDU đang sử dụng | XJTU |
| --- | --- | --- |
| Hãng | Lishen | Lishen |
| Dạng pin | LR1865SZ, tế bào trụ | 18650, tế bào trụ |
| Hóa học cathode | NMC(532) | NCM, công thức LiNi0.5Co0.2Mn0.3O2 theo tài liệu gốc |
| Dung lượng danh định | 2,4 Ah | 2,0 Ah |
| Số tế bào | 86 | 55 |
| Tín hiệu | Thời gian, V, I, T, dung lượng | Thời gian, V, I, T, dung lượng; có bảng tổng hợp chu kỳ |
| Quy trình xả dùng cho bài toán | Các chu kỳ tham chiếu khoảng 0,2C | Tùy batch: 1C, biến thiên dòng, xả ngẫu nhiên; một số chu kỳ đo tham chiếu riêng |
| Giai đoạn sử dụng | Ban đầu và tái sử dụng | Lão hóa theo sáu chiến lược thí nghiệm |
| BMS trên xe thực tế | Không | Không |

NCM và NMC đều chỉ họ vật liệu nickel/cobalt/manganese; không suy ra cùng model pin chỉ từ tên gọi. Dung lượng XJTU thấp hơn SDU khoảng 16,7%. Cùng hãng và họ vật liệu không bảo đảm mô hình SDU dự đoán đúng mà không hiệu chỉnh. Chưa xác minh vật liệu anode XJTU từ mô tả đã đọc.

## Đã tải và kiểm tra gì?

Đã đọc danh mục ZIP gốc và hai tài liệu Data Introduction (English/Chinese), tải nguyên một thành viên `Battery Dataset/Batch-1/2C_battery-1.mat` bằng HTTP Range, giải nén với kiểm tra CRC của ZIP. Không tải toàn bộ ZIP 2.438.769.934 byte (khoảng 2,44 GB thập phân).

File mẫu đầy đủ 44.388.077 byte, SHA-256 `336a0c25c9d6e4c18a231c0b4004edfb44fbd7808533490cddf4d073ce854dbb`. Đọc bằng scipy.io.loadmat:

- 390 phần tử chu kỳ, tổng 2.702.101 điểm đo.
- Có system_time, relative_time_min, voltage_V, current_A, capacity_Ah, power_Wh, temperature_C, description.
- Không có NaN/Inf trong năm trường số đã kiểm tra: thời gian tương đối, điện áp, dòng điện, dung lượng và nhiệt độ của file mẫu.
- Có summary.discharge_capacity_Ah và thông tin tổng hợp chu kỳ.
- Chưa kiểm tra toàn bộ 55 pin, điểm trùng, đồng bộ thời gian hoặc tính đúng đắn vật lý của mọi điểm. Không gọi toàn bộ bộ dữ liệu đã sạch chỉ từ kết quả mẫu.

Tài liệu gốc nêu dữ liệu được lấy mẫu 1 Hz, thí nghiệm từ 16/09/2022 đến 18/02/2023, sáu chiến lược; pin đạt kết thúc thí nghiệm theo tiêu chí dung lượng dưới 80% ban đầu. Đây là thông tin tác giả công bố, chưa được tái kiểm chứng trên cả 55 file.

## Phần phù hợp và phần cần xử lý riêng

XJTU phù hợp nghiên cứu phân tích suy giảm và xây dựng mô hình SOH. Nếu dùng làm kiểm thử ngoài nguồn:

1. Đọc cấu trúc MAT và mô tả từng batch, xác minh thời gian tương đối có reset giữa các bước trước khi tính độ dốc/tích phân. Không sửa dữ liệu gốc.
2. Tách sạc/xả/nghỉ và đối chiếu dung lượng từng chu kỳ với bảng summary. Không dùng điện lượng một đoạn xả chưa đầy đủ thay dung lượng tham chiếu của cả pin.
3. Quy định rõ SOH theo dung lượng danh định 2 Ah hay dung lượng đầu đời. Chọn định nghĩa nhất quán với câu hỏi đánh giá; không tiếp tục chia 2,4 Ah như SDU.
4. Giữ cửa sổ đầu vào 120 giây nếu đủ mẫu; phân tích khác biệt dòng C-rate và nhiệt độ. Thay đổi chuẩn hóa/đặc trưng cần được học trên phần huấn luyện, không điều chỉnh theo kết quả pin kiểm thử.
5. Thử chuyển miền trực tiếp chỉ như một thực nghiệm đo giới hạn. Nếu cần huấn luyện hoặc hiệu chỉnh lại, tách rõ khỏi kết quả chuyển miền trực tiếp và giữ riêng pin XJTU kiểm tra.
6. Bắt đầu khảo sát Batch-1/Batch-2 vì quy trình xả cố định dễ giải thích hơn, nhưng lưu ý đa số chu kỳ xả 1C khác SDU 0,2C. Batch-6 mô phỏng vệ tinh, không chọn làm minh chứng xe điện chỉ vì có dữ liệu.

Không dùng kết quả XJTU để ghi “đã kiểm chứng BMS trên xe”. Kết luận phù hợp là “kiểm thử bổ sung trên một bộ dữ liệu tế bào pin độc lập” nếu thực nghiệm đó thực sự được thực hiện và báo cáo đầy đủ.

Bằng chứng kiểm tra mẫu: `reports/xjtu_source_check.json`. Dữ liệu gốc được giữ riêng tại môi trường làm việc, chưa thêm vào ứng dụng hoặc bộ cài.
