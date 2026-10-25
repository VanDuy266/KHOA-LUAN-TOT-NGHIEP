# Dữ liệu BMS trên xe — BAIC EU500

Nguồn chính vẫn là SDU. Phần bổ sung trên giao diện đã chuyển từ XJTU (thử nghiệm cell trong lab) sang dữ liệu sạc thực tế trên xe. Kết quả XJTU trước đây được giữ trong `reports/xjtu`, `data/xjtu` và `docs/thuc-nghiem-xjtu.md` để đối chiếu lịch sử; không đổi tên các kết quả đó thành BMS.

## Nguồn và mức phù hợp

Deng, Z., Xu, L., Liu, H., Hu, X., Duan, Z., & Xu, Y. (2023). *Prognostics of battery capacity based on charging data and data-driven methods for on-road vehicles*. Applied Energy 339, 120954. https://doi.org/10.1016/j.apenergy.2023.120954

Kho của nhóm tác giả: https://github.com/BatICM/battery-charging-data-of-on-road-electric-vehicles (chuyển từ tài khoản TengMichael). Kho công bố kèm MIT License; giữ bản gốc tại `data/bms/provenance/deng_LICENSE` và yêu cầu trích dẫn trong README tác giả.

20 xe thương mại BAIC EU500, pin CATL NCM 145 Ah, 90 cell nối tiếp, 32 cảm biến nhiệt. Theo dõi khoảng 29 tháng. Tín hiệu sạc nhận qua CAN tại thiết bị sạc, khoảng 8 giây/mẫu. Các cột thực tế: thời gian, SOC, điện áp pack, dòng sạc, điện áp cell min/max, nhiệt độ min/max, available_energy và available_capacity.

Phù hợp cho thực nghiệm BMS trên xe và ước lượng dung lượng suy ra từ vận hành. Không phải bộ dữ liệu chạy xe đầy đủ; không có RPT dung lượng độc lập. Không đủ căn cứ để gọi đây là kiểm chứng SOH vật lý độc lập, kiểm chứng xe ở Việt Nam, hoặc chứng minh mô hình SDU chuyển giao trực tiếp.

## Nhãn và thay đổi so với tác giả

Tác giả suy ra dung lượng bằng tích phân dòng sạc chia độ tăng SOC, rồi thống kê theo tháng. Đây là nhãn từ vận hành, chịu sai số cảm biến và SOC BMS; không phải kết quả đo dung lượng toàn chu kỳ có kiểm soát.

Thực nghiệm của dự án có điều chỉnh được công bố rõ:

- Đầu vào: chỉ 0–120 giây đầu một phiên sạc. Đặc trưng nằm trong `src/battery_soh/bms.py`.
- Tạo tham chiếu riêng từ **phần sau 120 giây**, ít nhất 100 mẫu, SOC tăng ít nhất 20 điểm phần trăm. Không dùng chung các điểm dòng điện trong cửa sổ đặc trưng để tính nhãn.
- `Q_suy_ra = integral(-I dt) / 3600 / (delta_SOC / 100)`.
- Trung vị Q theo xe-tháng; cần ít nhất 3 phiên đủ điều kiện. `SOH_suy_ra = median(Q) / 145 * 100`. Không cắt kết quả về 0–100% để che dao động.
- Phiên tách khi khoảng thời gian >10 giây. Loại dữ liệu lỗi, phiên quá ngắn, SOC đi lùi >0,1 điểm hoặc nhảy >2 điểm mỗi bước, không đủ dòng sạc hoặc không đủ phần tạo nhãn. Loại dung lượng không dương hoặc trên 130% danh định theo kiểm tra hợp lệ đã định trước. Báo số loại theo xe và lý do.
- Không đưa `available_capacity`, `available_energy`, dung lượng, nhãn SOH, mã xe hay thời gian lịch vào đặc trưng.

Nhãn tháng dùng các phiên cùng tháng, nên đây là ước lượng trạng thái theo tháng, không phải dự báo tương lai theo thời gian. Dù phần dòng tạo nhãn tách khỏi cửa sổ đầu vào, nhãn và đầu vào vẫn thuộc cùng hệ thống cảm biến BMS, có sai số liên quan. Không xem nhãn suy ra là ground truth độc lập.

## Huấn luyện và đánh giá

5 vòng GroupKFold theo mã xe. Toàn bộ phiên của một xe cùng phía học/kiểm thử. Chuẩn hóa chỉ học trên train. So sánh mốc trung bình, Ridge, Random Forest và Ridge–RF hiệu chỉnh phần dư với cấu hình cố định. MAE/RMSE/R² tính từng xe rồi trung bình đều theo xe. Không chọn cấu hình theo xe test.

Mô hình BMS học riêng; không đưa điện áp pack vào mô hình SDU 2,4 Ah. Điểm BMS chỉ đo sự phù hợp với nhãn suy ra, không được so trực tiếp với MAE SDU hoặc kết quả bài báo gốc. Mô hình bàn giao được fit lại trên toàn bộ dữ liệu; dự đoán mẫu trong ứng dụng chỉ là minh họa. Kết quả giữ riêng nằm riêng trong bảng predictions và trang đánh giá.

## Tái lập

```powershell
.\.venv\Scripts\python.exe scripts\download_bms.py
.\.venv\Scripts\python.exe scripts\build_bms.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_bms.py -v
```

Cần `tar.exe` đi kèm Windows để đọc RAR, các thư viện học máy hiện có trong dự án. File nguồn được giữ nguyên; hash từng file và URL cố định trong `data/bms/provenance/source_manifest.json`. Báo cáo chi tiết: `reports/bms/dataset_summary.json`, `features.csv`, `monthly_reference.csv`, `metrics_summary.csv`, `metrics_by_vehicle.csv`, `timings.csv`, `predictions.csv`.

## Những nguồn đã đối chiếu

- **EVBattery/Tsinghua**: https://doi.org/10.6084/m9.figshare.23301881 và https://arxiv.org/html/2201.12358v3. Dữ liệu sạc xe thật; có ẩn danh/biến đổi tín hiệu; capacity là điện lượng ở đoạn điện áp xác định, health label là nhãn bất thường. Không tự chuyển thành SOH dung lượng đầy đủ. Liên kết file Figshare trả HTTP 403 trong lần kiểm tra này.
- **TUM UDS**: https://github.com/TUMFTM/electric-vehicle-uds-dataset. Xe thật và tín hiệu qua OBD/UDS, nhưng bảng tín hiệu đã đọc không có nhãn dung lượng/SOH độc lập. Lưu `tum_value_overview.csv` trong provenance. Chưa chọn cho kiểm thử SOH có nhãn.
- **IVST 300 xe**: https://ivstskl.changan.com.cn/?p=2697 và https://doi.org/10.1038/s41467-025-56485-7. Dữ liệu xe thật, nhãn SOH được suy ra và hiệu chỉnh bằng OCV–SOC; truy cập mẫu đi qua trang đăng ký. Không tự điền hoặc gửi thông tin người dùng.

## Kết quả chạy tại dự án

Đã đọc 16,100,728 bản ghi nguồn của 20 xe. Sau lọc: 27,205 phiên, 569 nhãn xe–tháng. Số phiên không phải số phép đo SOH độc lập.

| Mô hình | MAE (điểm % SOH suy ra) | RMSE | R² |
| --- | ---: | ---: | ---: |
| Mean baseline | 3.320 | 3.978 | -0.042 |
| Ridge | 2.805 | 3.416 | 0.222 |
| Random Forest | 2.172 | 2.832 | 0.467 |
| Ridge-RF residual | 2.100 | 2.729 | 0.504 |

Chỉ số trung bình đều theo xe ở 5 vòng giữ riêng xe; tham số cố định, chưa có RPT độc lập. Không dùng điểm này để suy rộng độ chính xác SOH vật lý. 7 kiểm thử BMS và kiểm tra mở 11 trang đều đạt; hash kết quả lưu trong `reports/bms/verification.json`.
