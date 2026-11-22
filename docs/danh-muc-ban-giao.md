# Danh mục bàn giao

| Thành phần | Vị trí |
| --- | --- |
| Báo cáo nội dung | `docs/bao-cao-khoa-luan.docx`, `.md`, `.pdf` |
| Slide trình bày | `docs/slide-bao-ve.pptx` |
| Mã nguồn ứng dụng | `webapp/`, `app/`, `src/`, `scripts/`, `tests/` |
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

Giám sát xu hướng: `src/battery_soh/anomaly.py`, `scripts/analyze_anomalies.py`, `reports/anomaly_*.csv`, `reports/anomaly_metadata.json`, `artifacts/anomaly_iforest.joblib`. Thực nghiệm BAIC dùng dữ liệu BMS trên xe với nhãn SOH suy ra từ dòng điện/SOC. Xem [phương pháp và giới hạn](thuc-nghiem-bms.md).

## XJTU và bộ giữa kỳ 10/11/2026

- Báo cáo tiến độ Word/PDF: docs/bao-cao-giua-ky-10-11-2026.
- Slide giữa kỳ PPTX/PDF: docs/slide-giua-ky-10-11-2026; 12 trang, PPTX có ghi chú trình bày.
- Phần thực nghiệm: docs/thuc-nghiem-xjtu.md, reports/xjtu và notebooks/03_thuc_nghiem_xjtu.ipynb.
- Dữ liệu dẫn xuất: data/xjtu/processed; nguồn và cách tải: data/xjtu/README.md, source_manifest.json.
- Mô hình ứng dụng: artifacts/xjtu/random_forest.joblib và multi_source_forest.joblib trong gói sản phẩm; có thể refit từ bảng nhỏ bằng scripts/save_xjtu_models.py.
- MAT gốc không kèm ZIP ứng dụng. Tải 23 file Batch-1/2 bằng scripts/download_xjtu.py; không cần tải lại hoặc huấn luyện để xem kết quả đóng gói.

Bản giữa kỳ là hồ sơ tiến độ. Mẫu nộp và yêu cầu nghiệm thu cuối kỳ cần theo giảng viên/trường; phần XJTU của bản giữa kỳ dùng dữ liệu tế bào trong phòng thí nghiệm.

## Đối chiếu chức năng web

| Mục | Thao tác và kết quả | Kiểm thử hiện có |
| --- | --- | --- |
| Sức khỏe pin | Chọn SDU, BAIC, dung lượng đo hoặc tín hiệu V/I/T. Kiểm tra đầu vào, xem kết quả tương ứng và xuất phiếu | `test_assessment.py`, `test_capacity_measurement.py`, `test_bms_assessment.py`, `browser_assessment.cjs` |
| Lịch sử | Mở, so sánh và theo dõi hồ sơ theo mã pin, tải bản sao JSON rồi khôi phục trên trình duyệt | `test_records.py`, hai kịch bản Chromium |
| Xu hướng dung lượng | Chọn lịch sử hoặc tải CSV, xem xu hướng và ước lượng vị trí chạm ngưỡng khi đủ điều kiện | `test_health.py`, `browser_workbench.cjs` |
| Phân loại lỗi | Chọn mẫu hoặc tải ma trận điện áp, xem dấu hiệu ở từng cell và đối chiếu nhãn nguồn nếu có | `test_fault.py`, `browser_workbench.cjs` |
| So sánh mô hình | Đọc MAE, RMSE, R² và thời gian thực nghiệm theo từng nguồn. Xem thử nghiệm trên pin giữ riêng | `test_web.py`, `test_benchmark_packaging.py`, `test_demo.py` |
| Huấn luyện | Dùng CSV đặc trưng có nhãn, đánh giá trên nhóm pin giữ riêng, tải gói kết quả | `test_training.py`, `browser_workbench.cjs` |
| Mô hình riêng | Trích đặc trưng từ tín hiệu hoặc dùng Ridge JSON để dự đoán bảng mới đúng miền | `test_custom_model.py`, `browser_workbench.cjs` |
| Định dạng dữ liệu | Tra cột và đơn vị trước khi tải lên, kiểm tra ánh xạ và lọc nhóm phù hợp | `test_column_mapping.py`, `test_filter_safety.py`, hai kịch bản Chromium |
| Thông tin đề tài | Tra thông tin tác giả, phương pháp, dữ liệu và tài liệu khóa luận | [Phạm vi và ba nguồn dữ liệu](pham-vi-de-tai.md) |

Để trình diễn, bắt đầu ở Sức khỏe pin với mẫu SDU, tải phiếu và lưu một hồ sơ. Sau đó mở Lịch sử để tra hồ sơ, thử mẫu ở Xu hướng dung lượng và Phân loại lỗi, rồi so sánh chỉ số SDU với các mô hình cùng nguồn. Ở Huấn luyện, dùng CSV mẫu có nhãn để tạo Ridge JSON và chuyển sang Mô hình riêng để thử suy luận. [Hướng dẫn đánh giá pin](huong-dan-danh-gia-pin.md) · [Hướng dẫn huấn luyện](training-workspace.md)

Khi bàn giao nghiên cứu, dùng đúng nguồn cho từng kết luận. BAIC có nhãn SOH suy ra và còn thiếu dung lượng RPT độc lập. Dự báo chạm ngưỡng là ngoại suy theo lịch sử quan sát. Phân loại lỗi dùng nguồn 99 xe riêng và chỉ áp dụng cho đầu vào cùng miền. Các yêu cầu nộp cuối kỳ cần đối chiếu với biểu mẫu và tiêu chí của khoa. [Phạm vi đề tài](pham-vi-de-tai.md) · [Dự báo và phân loại lỗi](health-and-fault.md)
