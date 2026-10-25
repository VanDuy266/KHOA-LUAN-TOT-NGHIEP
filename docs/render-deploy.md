# Vincent D trên Render — web HTML riêng

Ứng dụng chạy Flask với Gunicorn trên Render, Waitress trên Windows. Không dùng Streamlit để phục vụ trang.

## Dịch vụ đã có

Dịch vụ chính: `khoaluantotnghiep-vincentd`. Web: https://khoaluantotnghiep-vincentd.onrender.com/. Nhánh: `main`. Root Directory: để trống.

- Build Command: `python -m pip install -r requirements-render.txt && python scripts/check_hosting.py`
- Start Command: `python scripts/start_render.py`
- Health Check Path: `/healthz`
- Python 3.12 theo `.python-version`.

`requirements.txt` cũng trỏ về bộ phụ thuộc web để tương thích dịch vụ cũ đang dùng lệnh `pip install -r requirements.txt`. Start Command không đổi so với cấu hình đã sửa. Đường dẫn health cũ vẫn trả 200 để dịch vụ đã tạo tiếp tục hoạt động.

## Cập nhật

Sửa `webapp/templates/index.html`, `webapp/static/app.css`, `webapp/static/app.js` hoặc API `webapp/server.py` trong VS Code. Đẩy lên nhánh GitHub đã chọn; Auto Deploy triển khai nếu bật, hoặc chọn Deploy latest commit. Chỉ xác nhận thành công sau khi bản triển khai Live và trang/API hoạt động. Không cần tạo link mới.

## Dữ liệu và quyền riêng tư

Mô hình, cách chia tập và điểm kiểm thử giữ nguyên. Không huấn luyện khi khởi động. Chỉ có các bảng dẫn xuất và mô hình BMS cần cho web, không đưa RAR nguồn lên máy chủ. CSV upload giới hạn 20 MiB, dữ liệu giải nén tối đa 50 MiB, tối đa 2.000 chu kỳ theo quy tắc SDU. Lịch sử nằm trong sessionStorage của tab, không dùng SQLite chung giữa người dùng.

HTML trả ngay tiêu đề và metadata Vincent D cho crawler; không cần chạy JavaScript để lấy tên đề tài. Bản xem trước tin nhắn cũ có thể còn được ứng dụng nhắn tin lưu cache. Gói Render Free vẫn có thể ngủ khi không có truy cập; đổi giao diện không loại bỏ giới hạn hosting này.

## Chạy trên Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\chay_windows.ps1
```

Mở `http://localhost:8501`. Có thể đổi cổng bằng biến `PORT`. Kiểm thử web: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_web.py`.
