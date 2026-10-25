# Chạy trên Render

Mã khởi động chính: `app/streamlit_app.py`. Không dùng file trong thư mục backup.

## Web Service đã tạo

Render không tự áp dụng render.yaml cho dịch vụ đã tạo thủ công. Trong Settings của dịch vụ, đặt:

- Root Directory: để trống.
- Build Command: `python -m pip install -r requirements-render.txt && python scripts/check_hosting.py`
- Start Command: `python scripts/start_render.py`
- Health Check Path: `/_stcore/health`
- Python: 3.12 (file .python-version).

Phải đẩy các file mới, dữ liệu và mô hình tương ứng lên đúng nhánh dịch vụ đang theo dõi trước khi Deploy latest commit. Bản trên máy không tự đồng bộ lên GitHub.

## Blueprint mới

Dùng render.yaml tại thư mục gốc. Không tạo thêm dịch vụ nếu đang dùng dịch vụ hiện có.

Bản công khai giới hạn upload 20 MiB và chỉ giữ lịch sử theo phiên. Không cần huấn luyện khi khởi động. Gói Free có thể ngủ và có giới hạn RAM; cần kiểm tra Logs nếu tiến trình bị dừng.
