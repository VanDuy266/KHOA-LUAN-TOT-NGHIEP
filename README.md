# Khóa luận: Phân tích và dự đoán tình trạng sức khỏe pin xe điện bằng các mô hình học máy

Sinh viên: **Nguyễn Văn Duy** · MSSV: **2311553949** · Lớp: **23DTH2A**. Giảng viên theo phiếu đăng ký: **ThS. Vương Xuân Chí**.

Dự án có pipeline SOH, thực nghiệm leave-one-battery-out, ứng dụng Streamlit, kiểm thử, báo cáo và slide. Đây là bản triển khai nghiên cứu trên cell lithium-ion, chưa được xác nhận trên xe điện thực tế hoặc nghiệm thu bởi giảng viên.

## Tải bộ bàn giao

[Tải ZIP gồm mã nguồn, dữ liệu, mô hình và tài liệu](delivery/KhoaLuan_NguyenVanDuy.zip?raw=true). SHA-256 của gói nằm trong `delivery/KhoaLuan_NguyenVanDuy.sha256`.

Giải nén, mở thư mục `KHOA-LUAN-TOT-NGHIEP`, rồi làm theo hướng dẫn chạy dưới đây. Gói không chứa môi trường Python `.venv`; hãy chạy setup để cài thư viện. Nếu GitHub chỉ hiển thị thông tin file ZIP, chọn **Download raw file** để tải.

## Chạy lại

Yêu cầu Python 3.12; khoảng 1 GB dung lượng trống. Chạy từ thư mục repository:

```bash
bash scripts/setup.sh
.venv/bin/python -m streamlit run app/streamlit_app.py --server.headless=true --server.address=0.0.0.0 --server.port=8501
```

Setup cài từ lockfile, tải 8 CSV đã ghim checksum, huấn luyện trên 3 pin chính, chạy kiểm thử và tạo tài liệu. Không cần API key. Cần truy cập PyPI và raw.githubusercontent.com. Không tải mô hình joblib từ người dùng hoặc nguồn không tin cậy.

Chạy riêng các bước:

```bash
.venv/bin/python scripts/download_data.py
.venv/bin/python scripts/run_experiment.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/build_documents.py
.venv/bin/python scripts/build_notebook.py
```

## Thiết kế và kết quả

- Nhãn: `SOH (%) = 100 × capacity (Ah) / 2 Ah`. Đã kiểm tra nhãn với cột SOH của nguồn chuyển đổi.
- Đầu vào: số chu kỳ và thống kê điện áp, dòng điện, nhiệt độ trong 120 giây đầu. Không sử dụng dung lượng xả, SOH nhãn hoặc thời gian xả toàn chu kỳ.
- Ba pin B05/B07/B18, 468 chu kỳ; giữ toàn bộ một pin làm kiểm thử ở mỗi vòng. Không tinh chỉnh bằng tập kiểm thử.
- Random Forest: macro MAE 1,241; RMSE 1,628 điểm phần trăm SOH. Cycle Ridge: MAE 4,392.
- Mô hình demo Random Forest được chọn cố định trước khi xem điểm số, rồi huấn luyện lại trên tất cả dữ liệu chính. Dự đoán demo trên CSV mẫu không phải kết quả kiểm thử.

Các số liệu đầy đủ nằm trong `reports/metrics_by_battery.csv`, `reports/metrics_summary.csv` và `reports/run_metadata.json`.

## Dữ liệu và giới hạn

CSV do repository công khai `standing-o/SoH_estimation_of_Lithium-ion_battery` chuyển đổi, dẫn nguồn NASA. Commit và SHA-256 nằm trong `data/manifest.json`; giấy phép của repository nguồn được giữ trong `data/SOURCE_LICENSE.txt`. Checksum xác nhận đúng phiên bản chuyển đổi, không xác nhận đúng với NASA gốc.

Chưa truy cập được NASA/CALCE gốc do chính sách mạng. B05/B07 có trục thời gian giống nhau hoàn toàn trong CSV; đây là dấu hiệu cần đối chiếu bước chuyển đổi. Các pin bổ sung có SOH rất thấp hoặc dung lượng bằng 0 nên chỉ được kiểm kê, chưa dùng cho kết luận chính. Vì vậy kết quả là **thực nghiệm trên bản chuyển đổi**, chưa đủ làm bằng chứng chất lượng trên dữ liệu gốc hoặc pin xe điện thực tế. Không khẳng định kết quả đạt yêu cầu nộp khóa luận trước khi giảng viên duyệt nguồn dữ liệu và hình thức báo cáo.

## Các tệp chính

| Đường dẫn | Nội dung |
| --- | --- |
| `docs/bao-cao-khoa-luan.md` | Báo cáo với kết quả thực đo và hạn chế |
| `docs/bao-cao-khoa-luan.docx` | Bản Word để chỉnh theo mẫu trường |
| `docs/slide-bao-ve.pptx` | Slide trình bày |
| `docs/huong-dan-bao-ve.md` | Kịch bản demo và câu hỏi thường gặp |
| `notebooks/01_eda.ipynb` | Notebook khám phá dữ liệu đã thực thi |
| `src/battery_soh/features.py` | Kiểm tra dữ liệu và đặc trưng cửa sổ |
| `scripts/run_experiment.py` | So sánh mô hình và lưu kết quả |
| `app/streamlit_app.py` | Ứng dụng minh họa tiếng Việt |
| `tests/` | Kiểm thử chống rò rỉ, dữ liệu và luồng demo |

Dữ liệu và mô hình sinh ra được bỏ qua bởi Git; chạy setup để khôi phục. Kết quả CSV, hình và tài liệu được giữ để xem xét. Không tự động commit, push hay Publish.
