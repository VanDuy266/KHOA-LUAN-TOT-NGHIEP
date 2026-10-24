# XJTU — thực nghiệm bổ sung

Nguồn: https://zenodo.org/records/10963339, DOI 10.5281/zenodo.10963339, Fujin Wang (Xi'an Jiaotong University), 2024, CC BY 4.0. Bài báo: https://doi.org/10.1038/s41467-024-48779-z.

Chọn Batch-1 (8 pin) và Batch-2 (15 pin), Lishen 18650 NCM danh định 2 Ah. Nguồn có 55 pin, nhưng phần mở rộng này dùng 23 pin có quy trình cố định. Chu kỳ đầu 0,2C không đưa vào đánh giá xả 1C chính. Hai batch có chiến lược sạc 2C/3C, khác với điều kiện tham chiếu SDU.

- `source_manifest.json`: tên thành viên ZIP, CRC và SHA-256 của MAT đã tải. Bản sao bằng chứng nằm ở reports/xjtu/source_manifest.json.
- `raw/`: file MAT nguyên gốc, không sửa; thư mục này không đưa vào Git và ZIP ứng dụng. Chạy scripts/download_xjtu.py để tải đúng các file từ ZIP tác giả.
- `processed/`: cửa sổ đầu xả và chuỗi GRU dẫn xuất, không thay thế nguồn gốc.
- `reports/xjtu/`: bảng đặc trưng, nhãn, kiểm tra, dự đoán pin giữ riêng và chỉ số. Các chỉ số tách khỏi SDU.

SOH = dung lượng xả summary / 2 Ah × 100. V/I/T trong 120 giây đầu tạo đặc trưng; dung lượng đo và SOH không là đặc trưng đầu vào. Đồng hồ system_time dùng để nhận diện cửa sổ, phép đo cùng giây chỉ gộp tại bảng dẫn xuất. Không dùng relative_time_min làm thời gian toàn chu kỳ vì có thể reset theo bước.

Tái lập từ nguồn (cài requirements.txt và requirements-deep.txt trước):

```powershell
.\.venv\Scripts\python.exe scripts\download_xjtu.py
.\.venv\Scripts\python.exe scripts\prepare_xjtu.py
.\.venv\Scripts\python.exe scripts\evaluate_xjtu.py
.\.venv\Scripts\python.exe scripts\build_xjtu_documents.py
```

Mô hình ứng dụng có sẵn trong gói sản phẩm. Nếu chỉ lấy mã nguồn và bảng dẫn xuất, có thể refit hai RF bằng scripts/save_xjtu_models.py, không cần tải MAT hoặc cài PyTorch để chạy giao diện. Thực nghiệm đầy đủ có GRU cần requirements-deep.txt.

Không phải dữ liệu BMS trên xe; chưa triển khai RUL. Không gọi kết quả này là kiểm chứng trên xe thương mại.

Tài liệu tác giả trong ZIP gốc được giữ tại `provenance/Data_Introduction_English.pdf` để đối chiếu điều kiện thử. Giấy phép nguồn: https://creativecommons.org/licenses/by/4.0/; ghi công Fujin Wang và trích DOI bộ dữ liệu/bài báo khi sử dụng.
