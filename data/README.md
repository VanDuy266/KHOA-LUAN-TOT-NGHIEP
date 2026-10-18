# Bộ dữ liệu pin sạch: 2.089.048 dòng đo

Đây là phép đo của **4 cell lithium-ion**, được NASA PCoE công bố theo danh mục chính thức [1]. File MATLAB được tải từ bản lưu công khai [2], ghim commit trong `manifest.json`. Dữ liệu **không phải của Việt Nam**. Đã đọc trang NASA và README thí nghiệm; chưa so sánh byte với archive S3 của đơn vị phát hành vì đường tải đó bị chặn.

## Số lượng thực tế

| Pin | Dòng sạc sạch | Dòng xả | Tổng dòng sạch | Chu kỳ xả / mẫu SOH |
| --- | ---: | ---: | ---: | ---: |
| B0005 | 541.173 | 50.285 | 591.458 | 168 |
| B0006 | 541.173 | 50.285 | 591.458 | 168 |
| B0007 | 541.173 | 50.285 | 591.458 | 168 |
| B0018 | 279.808 | 34.866 | 314.674 | 132 |
| **Tổng** | **1.903.327** | **185.721** | **2.089.048** | **636** |

Nguồn có 2.089.050 dòng sạc/xả. Loại đúng **2 dòng sạc thiếu tín hiệu** tại B0018, operation 115, thời gian 4528.156 và 4786.328 giây. Không nội suy, không nhân bản để tăng số lượng. Không trộn phép đo trở kháng vì cấu trúc khác.

## Các file CSV

- `clean/measurements_all.csv`: 2.089.048 dòng, 9 cột, gồm sạc và xả; **không có nhãn SOH cho phần sạc**.
- `clean/measurements.csv`: 185.721 dòng xả, có capacity (Ah) và SOH (tỷ lệ, chưa nhân 100).
- `clean/cycle_features.csv`: 636 dòng, 13 cột, gồm mã pin, nhãn `soh_pct` và 11 đặc trưng. Đây mới là bảng đưa vào mô hình SOH.

Các file sinh ra được bỏ qua bởi Git; tải gói dataset ZIP hoặc chạy `scripts/download_data.py` rồi `scripts/prepare_data.py`.

## Từ điển cột bảng toàn bộ phép đo

| Cột | Kiểu / đơn vị | Ý nghĩa |
| --- | --- | --- |
| battery | chuỗi | Mã cell, không phải mã xe |
| operation_type | charge / discharge | Loại hoạt động sạc hoặc xả |
| operation_index | số nguyên | Thứ tự operation trong MATLAB; khóa cùng battery và time |
| cycle | số nguyên | Thứ tự sạc hoặc xả, đếm riêng theo operation_type |
| time | giây | Thời gian từ đầu operation, bắt đầu lại ở operation tiếp theo |
| terminal_voltage | V | Điện áp tại cell |
| terminal_current | A | Dòng đo; xả mang dấu âm |
| temperature | °C | Nhiệt độ cell |
| ambient_temperature | °C | Nhiệt độ môi trường ghi trong thí nghiệm |

Không dùng `cycle` để ghép sạc/xả như thể luôn một-một: có 170 lần sạc nhưng 168 lần xả ở B0005/B0006/B0007. Giữ operation_index để tái hiện trình tự thực.

## Quy tắc dùng cho khóa luận

SOH (%) = 100 × capacity / 2 Ah, dựa trên dung lượng danh định trong README thí nghiệm. B0006 có SOH ban đầu khoảng 101,77%; giữ nguyên thay vì cắt về 100%. Đặc trưng chỉ dùng 120 giây đầu của chu kỳ xả, không dùng capacity, SOH hoặc thời gian toàn chu kỳ làm đầu vào. Không gán dung lượng của lần xả sau cho từng dòng sạc rồi chia ngẫu nhiên để tăng số mẫu.

Hai triệu dòng đo không đồng nghĩa hai triệu pin hoặc hai triệu mẫu nhãn độc lập. Bài toán SOH hiện có 636 chu kỳ và 4 nhóm pin. Đánh giá chính phải giữ riêng toàn bộ một pin, không chia ngẫu nhiên các thời điểm của cùng pin.

## Kiểm chứng

`scripts/check_dataset.py` đọc CSV theo khối, xác minh trên 2 triệu dòng, không thiếu/vô hạn, không trùng khóa, thứ tự đúng và so sánh từng mảng tín hiệu với MATLAB sau khi loại hai dòng thiếu. Kết quả và SHA-256 CSV ở `reports/dataset_check.json`; nhật ký loại dòng ở `reports/removed_measurements.csv`.

`reports/source_comparison.csv` ghi đối chiếu 468 chu kỳ của B0005/B0007/B0018 với bản CSV cộng đồng trước đây: thời gian, điện áp, dung lượng và số mẫu khớp. Hiện tượng trục thời gian giống nhau giữa pin cũng tồn tại trong file MATLAB của bản lưu, không đủ cơ sở gọi là lỗi chuyển CSV. Chưa xác thực byte với archive chính thức nên vẫn lưu giới hạn nguồn.

## Nguồn và ghi công

1. B. Saha và K. Goebel (2007), **Battery Data Set**, NASA Prognostics Data Repository, NASA Ames Research Center. Danh mục: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/
2. Bản lưu MATLAB và README: https://github.com/psanabriaUC/BatteryDatasetImplementation/tree/0007aead10cb85aafdd11fb3de1d64186c7c6c05/battery_data
3. CSV cộng đồng dùng để đối chiếu bản cũ: https://github.com/standing-o/SoH_estimation_of_Lithium-ion_battery — `community_manifest.json` và `SOURCE_LICENSE.txt` chỉ áp dụng cho nguồn cộng đồng cũ, không gán giấy phép đó cho dữ liệu NASA hoặc toàn bộ dự án.

Chưa xác minh được bộ dữ liệu xe điện Việt Nam công khai đủ cấu trúc chu kỳ, dung lượng tham chiếu và quyền sử dụng tương đương. Nếu có dữ liệu từ phòng thí nghiệm/đơn vị vận hành trong nước, phải được phép sử dụng và kiểm tra đơn vị, ẩn thông tin nhận dạng xe trước khi thay nguồn.
