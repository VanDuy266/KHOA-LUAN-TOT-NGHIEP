# Nguồn dữ liệu HUST

- Trang dữ liệu: https://data.mendeley.com/datasets/nsc7hnsg4s/2
- Đường tải được đối chiếu từ mã nguồn Microsoft BatteryML, commit `2861ae3b8c79938c7fc8e6fe9986b799ca71c7dd`:
  https://github.com/microsoft/BatteryML/blob/2861ae3b8c79938c7fc8e6fe9986b799ca71c7dd/batteryml/preprocess/download.py
- BatteryML mô tả 77 pin LFP/graphite, dung lượng danh định 1,1 Ah. Đây là mô tả nguồn, chưa phải số lượng kiểm đếm từ file trong dự án.
- Năm công bố BatteryML là 2024; không dùng năm đó làm năm thu thập HUST.

## Trạng thái

Đường tải Mendeley bị chặn HTTP 403 trong môi trường hiện tại. Chưa tải được dữ liệu nên chưa xác định số dòng sạch. Chưa chuyển ứng dụng, mô hình hoặc kết quả NASA sang HUST.

Bộ xử lý HUST của BatteryML sử dụng điện áp, dòng điện và thời gian, không xuất nhiệt độ. Khi có file cần kiểm tra các cột thực tế; không tự điền nhiệt độ giả. Dung lượng danh định HUST là 1,1 Ah, khác NASA 2 Ah; phải tính lại nhãn SOH và huấn luyện lại.

## Tải trên máy cá nhân

Tại thư mục gốc dự án, chạy:

```powershell
.\.venv\Scripts\python.exe scripts\download_hust.py
```

Hoặc tải ZIP từ trang Mendeley rồi kiểm tra:

```powershell
.\.venv\Scripts\python.exe scripts\download_hust.py --archive "D:\Downloads\hust_data.zip"
```

Script kiểm tra cấu trúc, lỗi ZIP, tính SHA-256 và lưu nhật ký vào `data/hust/download_audit.json`. Mã SHA-256 này ghi nhận file đã tải, chưa xác nhận khớp với mã của tác giả. Script không đọc hoặc thực thi pickle trong ZIP.

Sau khi có dữ liệu cần kiểm đếm dòng, làm sạch theo pin/chu kỳ, kiểm tra dung lượng và thời gian, trích xuất đặc trưng, chia pin huấn luyện/kiểm thử và tạo lại toàn bộ kết quả. Không giới hạn số dòng ở 2 triệu và không áp dụng chỉ số sai số NASA cho HUST.
