# Danh mục bàn giao

| Thành phần | Vị trí |
| --- | --- |
| Báo cáo nội dung | `docs/bao-cao-khoa-luan.docx`, `.md`, `.pdf` |
| Slide trình bày | `docs/slide-bao-ve.pptx` |
| Mã nguồn ứng dụng | `app/`, `src/`, `scripts/`, `tests/` |
| Danh sách thư viện | `requirements-app.txt`, `requirements.txt`, `requirements-deep.txt`, `requirements.lock.txt` |
| Dữ liệu phục vụ sản phẩm | `data/clean/cells/`, `cycle_features.csv`, `cycle_labels.csv`, `sample_measurements.csv` |
| Mô hình đã học lại | `artifacts/` |
| Notebook đã thực thi | `notebooks/01_eda.ipynb` |
| Kết quả thực nghiệm | `reports/metrics_*.csv`, `predictions.csv`, `ablation_*.csv`, `temporal_*.csv` |
| Biểu đồ | `reports/*.png` |
| Cấu hình, phân hoạch và kiểm thử | `reports/run_metadata.json`, `gru_metadata.json`, `split_assignments.csv`, `pytest-results.xml` |
| Nguồn và kiểm tra dữ liệu | `data/README.md`, `data/KIEM_TRA_DU_LIEU.md`, `data/provenance/` |

## Bộ dữ liệu nộp riêng

Bộ dữ liệu ZIP gồm `source_rows/Primary_use_phase/` và `source_rows/Second_life_phase/`: tổng 172 file CSV gzip của cùng 86 pin. Kèm `training_table.csv`, `cycle_features.csv`, nguồn, nhật ký chọn và thư mục `verification/`. Giữ nguyên `.csv.gz`, không cần giải nén từng file. Gói này là tập con 10.505.065 dòng do dự án chọn từ nguồn SDU; không gọi là toàn bộ bộ nguồn 145 triệu dòng.

Nguồn gốc đầy đủ, giấy phép CC BY 4.0 và checksum được ghi trong hồ sơ. Gói sản phẩm chứa bản Parquet dẫn xuất để chạy nhanh, không thay thế việc lưu trữ nguồn và trích dẫn.

Tên trường, thông tin sinh viên và GVHD theo phiếu đăng ký. Quy định về biểu mẫu, chữ ký, số lượng bản in, số trang và thủ tục nộp cuối cùng do khoa/giảng viên xác nhận.
