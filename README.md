# Khóa luận: Phân tích và dự đoán tình trạng sức khỏe pin xe điện bằng các mô hình học máy

Nguyễn Văn Duy · MSSV 2311553949 · Lớp 23DTH2A · GVHD theo phiếu: ThS. Vương Xuân Chí.

Tôi sử dụng dữ liệu pin NASA để phân tích quá trình suy giảm dung lượng và dự đoán tình trạng sức khỏe pin (SOH). Ứng dụng **Vincent D** dùng để tra cứu dữ liệu, so sánh mô hình và dự đoán SOH từ file CSV.

Ngôn ngữ và thư viện: **Python 3.12, pandas, SciPy, scikit-learn, Matplotlib và Streamlit**.

## Tải về

- [Code, mô hình, dữ liệu xả, notebook, báo cáo Word và slide](delivery/KhoaLuan_NguyenVanDuy.zip?raw=true).
- [Dataset sạch đầy đủ 2.089.048 dòng](delivery/Dataset_Pin_NASA_2tr_dong.zip?raw=true).

Dữ liệu đầy đủ nằm trong gói riêng. Mỗi file ZIP có mã SHA-256 để kiểm tra khi tải. Gói mã nguồn không kèm môi trường `.venv`.

## Chạy sản phẩm trên Windows / VS Code

Yêu cầu Python 3.12. Chạy các lệnh sau trong PowerShell tại thư mục gốc của dự án:

```powershell
py -3.12 --version
powershell -ExecutionPolicy Bypass -File .\chay_windows.ps1
```

File `chay_windows.ps1` tạo môi trường, cài thư viện và chạy ứng dụng. Nếu máy chưa có Python 3.12, tải tại [python.org](https://www.python.org/downloads/).

Các lệnh chạy thủ công:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-app.txt
.\.venv\Scripts\python.exe scripts\download_data.py
.\.venv\Scripts\python.exe scripts\prepare_data.py
.\.venv\Scripts\python.exe scripts\run_experiment.py
.\.venv\Scripts\python.exe -m streamlit run app\streamlit_app.py
```

Những lần sau, chạy lệnh cuối để mở ứng dụng tại `http://localhost:8501`. Nhấn `Ctrl+C` để dừng.

## Chạy toàn bộ nghiên cứu và tạo lại tài liệu

Linux: `bash scripts/setup.sh`. Windows: cài `requirements.txt` thay cho `requirements-app.txt`, rồi chạy thêm `scripts/check_dataset.py`, `scripts/analyze_results.py`, `python -m pytest -q`, `scripts/build_notebook.py` và `scripts/build_documents.py` bằng Python của `.venv`.

Cần khoảng 2 GB ổ đĩa cho môi trường và CSV. Không cần GPU hoặc API key. `requirements-app.txt` chỉ cài phần chạy sản phẩm; `requirements.txt` thêm kiểm thử và xuất Word/PowerPoint/notebook; `requirements.lock.txt` ghim môi trường Linux đã kiểm thử. Môi trường kiểm thử hiện tại là Linux; script Windows chưa được kiểm thử trực tiếp trên Windows.

## Giao diện Vincent D

Thông tin hiển thị: **Nguyễn Văn Duy · MSSV 2311553949 · Chuyên ngành Khoa Học Dữ Liệu**.

| Mục | Chức năng |
| --- | --- |
| Tổng quan | Hồ sơ sinh viên, số liệu nghiên cứu, đường SOH của bốn pin |
| Tra cứu pin | Lọc pin/chu kỳ, xem tín hiệu và so sánh hai chu kỳ A/B, tải CSV |
| Đánh giá mô hình | So sánh MAE/RMSE/R², chọn mô hình và pin kiểm thử, xem sai số, phân tích bổ sung |
| Dự đoán SOH | Một chu kỳ hoặc theo lô tối đa 100 chu kỳ; lỗi theo nhóm; xuất CSV và phiếu HTML |
| Lịch sử dự đoán | Lưu tạm tối đa 500 chu kỳ trong phiên, lọc trạng thái, tải hoặc xóa |
| Thông tin | Nguồn, quy trình làm sạch, thuật ngữ và tải báo cáo/slide |

Giao diện dùng tiếng Việt và phông Arial. Kết quả có thể tải dưới dạng CSV hoặc phiếu HTML để in và lưu PDF. Chế độ dự đoán một chu kỳ nhận dữ liệu của một pin và một chu kỳ; chế độ theo lô nhận tối đa 100 chu kỳ. Lịch sử chỉ lưu trong phiên sử dụng.

![Tổng quan Vincent D](docs/images/00-tong-quan.png)

## Dữ liệu

| Nội dung | Số lượng |
| --- | ---: |
| Dòng sạc/xả ban đầu | 2.089.050 |
| Dòng sạc thiếu tín hiệu bị loại | 2 |
| Dòng sạch | **2.089.048** |
| Trong đó: dòng sạc sạch | 1.903.327 |
| Trong đó: dòng xả | 185.721 |
| Mẫu học máy theo chu kỳ xả | **636** |
| Pin độc lập | **4** |

Sau làm sạch, dữ liệu không còn giá trị thiếu, giá trị vô hạn hoặc trùng khóa. Số dòng được giữ theo dữ liệu gốc, không nhân bản hay nội suy. Chi tiết tại [nguồn và mô tả dữ liệu](data/README.md).

Dữ liệu thí nghiệm NASA tại Hoa Kỳ, gồm bốn pin. File MATLAB lấy từ bản lưu công khai có dẫn nguồn NASA và mã kiểm tra; chưa đối chiếu trực tiếp với file gốc trên S3 của NASA. Hơn hai triệu dòng đo tạo thành **636 mẫu theo chu kỳ xả**, không phải hai triệu mẫu SOH độc lập.

## Phương pháp và kết quả

- SOH (%) = 100 × dung lượng xả / 2 Ah. Giữ nguyên giá trị hơi trên 100% nếu dung lượng đo vượt danh định.
- 11 đặc trưng: số chu kỳ và thống kê điện áp, dòng, nhiệt độ trong 120 giây đầu xả. Không dùng capacity hoặc SOH làm đầu vào.
- Mỗi vòng dùng ba pin để huấn luyện và một pin để kiểm thử. Tổng cộng bốn vòng với năm cấu hình mô hình.
- Random Forest: macro MAE **2,724**, RMSE **3,189** điểm phần trăm SOH. Cycle Ridge: MAE **4,074**.
- Kiểm thử theo thời gian dùng 70% chu kỳ đầu để huấn luyện và 30% còn lại để đánh giá. Trong thử nghiệm này, Random Forest có sai số cao hơn cách lấy SOH cuối đã biết làm dự đoán. Đề tài chưa dự đoán tuổi thọ còn lại của pin.

Mô hình trong ứng dụng được huấn luyện trên cả bốn pin. Kết quả với CSV mẫu chỉ dùng để minh họa chức năng; chỉ số kiểm thử lấy từ các vòng giữ riêng từng pin.

## Cấu trúc dự án

| File / thư mục | Vai trò |
| --- | --- |
| `scripts/download_data.py` | Tải dữ liệu và kiểm tra checksum |
| `scripts/prepare_data.py` | Đọc MATLAB, làm sạch, xuất CSV và đặc trưng |
| `scripts/check_dataset.py` | Kiểm chứng toàn bộ dataset |
| `src/battery_soh/features.py` | Đặc trưng 120 giây dùng chung |
| `scripts/run_experiment.py` | Huấn luyện, kiểm thử và lưu mô hình |
| `scripts/analyze_results.py` | Bỏ đặc trưng, đánh giá theo thời gian |
| `app/streamlit_app.py` | Giao diện dữ liệu, kết quả và dự đoán CSV |
| `notebooks/01_eda.ipynb` | Notebook đã thực thi |
| `docs/giai-thich-code.md` | Giải thích mã nguồn |
| `docs/so-tay-hoc-va-bao-ve.md` | Phương pháp, mô hình và kết quả thực nghiệm |
| `docs/bao-cao-khoa-luan.docx` | Báo cáo có kết quả thực nghiệm |
| `docs/slide-bao-ve.pptx` | Slide bảo vệ |
| `reports/` | Thống kê, chỉ số, dự đoán test, hình và nhật ký |

## Phạm vi nghiên cứu

Tôi đánh giá mô hình trên bốn cell pin trong phòng thí nghiệm. Kết quả chưa được kiểm chứng trên bộ pin hoàn chỉnh hoặc xe điện tại Việt Nam.
