# Vincent D — Phân tích và dự đoán sức khỏe pin

**Nguyễn Văn Duy · MSSV 2311553949 · Khoa Học Dữ Liệu · Lớp 23DTH2A**

Trường Đại học Nguyễn Tất Thành · GVHD: ThS. Vương Xuân Chí

Tôi sử dụng dữ liệu SDU công bố năm 2025 để phân tích dung lượng và ước lượng SOH từ 120 giây đầu xả. Ứng dụng **Vincent D** cung cấp tra cứu hai giai đoạn sử dụng pin, so sánh chu kỳ, đánh giá mô hình và dự đoán từ CSV. Phần thực nghiệm bổ sung dùng dữ liệu BMS sạc của 20 xe BAIC EU500: mô hình học riêng, giữ riêng xe khi kiểm thử và ghi rõ nhãn SOH suy ra từ dòng điện/SOC. Xem `docs/thuc-nghiem-bms.md`; chưa có phép đo dung lượng RPT độc lập.

## Tải sản phẩm và dữ liệu

- [Bản sản phẩm đầy đủ, có dữ liệu tra cứu và mô hình](https://github.com/VanDuy266/KHOA-LUAN-TOT-NGHIEP/archive/refs/heads/san-pham-sdu.zip).
- [Bộ dữ liệu nguồn đã chọn — 10.505.065 dòng, một file ZIP](https://github.com/VanDuy266/KHOA-LUAN-TOT-NGHIEP/archive/refs/heads/dataset-sdu-10tr.zip).

Kho riêng tư yêu cầu đăng nhập tài khoản GitHub có quyền truy cập. Gói sản phẩm có sẵn Parquet, mô hình và kết quả; không cần tải nguồn hoặc huấn luyện lại để mở ứng dụng. Gói dữ liệu riêng dùng để đối chiếu nguồn hoặc tạo lại Parquet. Quy tắc lấy thưa: sau khi giữ cửa sổ đầu và điểm cuối, giữ mỗi ba điểm còn lại một điểm trong từng chu kỳ. Số dòng là kết quả đếm thực tế. Chỉ giải nén ZIP ngoài; Python đọc trực tiếp các file `.csv.gz` bên trong.

## Chạy trên Windows / VS Code

Cài Python **3.12**, giải nén gói sản phẩm, mở thư mục có `README.md`, `app`, `scripts` trong VS Code. Terminal PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\chay_windows.ps1
```

Hoặc chạy từng lệnh tại thư mục gốc dự án:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-render.txt
.\.venv\Scripts\python.exe scripts\start_render.py
```

Chờ cài thư viện hoàn tất. Nếu Python báo chưa có bản 3.12, cài bản này trước bằng `py install 3.12` nếu Launcher hỗ trợ, hoặc từ https://www.python.org/downloads/. Không chạy các lệnh `.venv` khi terminal đang ở thư mục `app`; dùng `cd ..` về gốc trước.

Trình duyệt mở địa chỉ máy chủ hiển thị trong terminal. Đổi trang không huấn luyện lại. Đóng các ứng dụng nặng trước khi xử lý lại dữ liệu hoặc huấn luyện; giới hạn 2 luồng CPU không thể bảo đảm máy không chậm nếu RAM đang gần đầy.

## Dữ liệu

| Nội dung | Quy mô |
| --- | ---: |
| Pin vật lý | 86 |
| Giai đoạn | 2 — sử dụng ban đầu và tái sử dụng |
| File đo trong bộ chọn | 172 CSV gzip |
| Dòng đo nguồn gốc | 145.112.317 |
| Dòng xả tham chiếu trước lấy thưa | 30.929.675 |
| Dòng đo được giữ trong bản sản phẩm | 10.505.065 |
| Mẫu chu kỳ dùng huấn luyện | 20.823 |
| Đặc trưng mô hình bảng | 12 |

Nguồn: Wang, S., Gao, F., & Tian, H. (2025). *Data for: Deep sorting of reused batteries for enabling long-term consistency grouping with unknown prior conditions*. Zenodo, [DOI 10.5281/zenodo.14859405](https://doi.org/10.5281/zenodo.14859405), CC BY 4.0. Bài báo liên quan: [10.1016/j.xcrp.2025.102657](https://doi.org/10.1016/j.xcrp.2025.102657).

Đây là tế bào Lishen LR1865SZ NMC(532)/graphite, 2,4 Ah trong phòng thí nghiệm Trung Quốc, chưa phải dữ liệu bộ pin xe chạy tại Việt Nam. Ngày công bố 2025 không có nghĩa mọi số đo được thu trong năm 2025.

Bản chọn giữ đủ các chu kỳ xả tham chiếu, mọi điểm 120 giây đầu và điểm cuối; lấy thưa đoạn sau. Không sửa giá trị các dòng nguồn. Bộ chọn không bao gồm mọi chế độ sạc, nghỉ và xả trong gói gốc. Nhãn dung lượng lấy từ chu kỳ đầy đủ, không tính lại trên bản đã lấy thưa.

Kiểm tra toàn bộ 10.505.065 dòng không phát hiện thiếu tín hiệu bắt buộc hoặc khóa thời gian trùng. Có **26 điểm nghi vấn**, không điểm nào trong cửa sổ mô hình; các điểm được giữ để xem xét. Có 23 bước thời gian đi lùi trong thứ tự nguồn; bản sao xử lý được sắp trong từng chu kỳ. Chi tiết tại [nguồn dữ liệu](data/README.md), [kết quả kiểm tra](data/KIEM_TRA_DU_LIEU.md) và `reports/dataset_check.json`.

## Mô hình và kết quả

Bốn mô hình: **Ridge, Random Forest, LightGBM, GRU**; thêm mốc dự đoán trung bình SOH. GroupKFold 5 vòng theo mã pin vật lý, seed 42; hai giai đoạn của một pin luôn ở cùng phía. Chuẩn hóa học trên train, không tối ưu tham số trên test. Chỉ số chính lấy trung bình không trọng số theo 86 pin.

| Mô hình | MAE (điểm % SOH) | RMSE | R² |
| --- | ---: | ---: | ---: |
| Trung bình SOH | 13,246 | 15,249 | −0,281 |
| Ridge | 2,582 | 3,299 | 0,933 |
| Random Forest | 1,619 | 2,157 | 0,970 |
| LightGBM | 1,734 | 2,270 | 0,968 |
| GRU | 2,141 | 2,718 | 0,953 |

GRU dùng chuỗi 25 vị trí V/I/T trong 120 giây cùng chu kỳ/giai đoạn; các mô hình bảng dùng 12 thống kê. Phép so sánh gồm cả khác biệt biểu diễn. MAE không phải “độ chính xác phần trăm”. Mô hình ứng dụng được học lại trên toàn bộ bảng và tách khỏi kết quả kiểm thử pin giữ riêng. CSV mẫu đã tham gia huấn luyện.

Kết quả theo giai đoạn, bỏ nhóm đặc trưng và kiểm thử thời gian nằm trong `reports/`. Điểm 70/30 theo thời gian không gộp với điểm kiểm thử pin mới. Chưa kiểm chứng trên xe thực tế, chưa dự báo RUL hoặc chứng nhận an toàn pin.

## Chạy lại thực nghiệm

Cài thư viện nghiên cứu trong cùng môi trường Python:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-research.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-deep.txt
```

Nếu cần tạo lại Parquet từ gói nguồn tải riêng:

```powershell
.\.venv\Scripts\python.exe scripts\download_data.py --zip "D:\DuLieu\KHOA-LUAN-TOT-NGHIEP-dataset-sdu-10tr.zip"
.\.venv\Scripts\python.exe scripts\prepare_data.py
```

Tái lập kiểm tra, huấn luyện và tài liệu:

```powershell
.\.venv\Scripts\python.exe scripts\reproduce.py
```

Các bước thực hiện lần lượt: `check_dataset.py` → `run_experiment.py` → `train_gru.py` → `analyze_results.py` → `save_models.py` → pytest → notebook → báo cáo/slide. Việc tái tạo từ bộ nguồn tác giả 145 triệu dòng được mô tả trong `data/provenance/`; đó là bước riêng, nặng hơn nhiều so với mở sản phẩm. Các script ở đó giữ theo cấu trúc bộ chọn ban đầu và có README riêng.

## Cấu trúc sản phẩm

| Thư mục | Nội dung |
| --- | --- |
| `app/` | 11 trang web riêng, dự đoán CSV, biểu đồ, lịch sử phiên và lưu kết quả tùy chọn trên máy chủ |
| `src/battery_soh/` | Hàm đặc trưng và kiểm nhãn dùng chung |
| `scripts/` | Nhận dữ liệu, chuyển đổi, huấn luyện, đánh giá, tạo tài liệu |
| `data/clean/` | Parquet theo pin/giai đoạn, mẫu CSV, bảng đặc trưng và nhãn |
| `data/provenance/` | Hồ sơ nguồn, nhật ký chọn và mã xây dựng bộ chọn |
| `artifacts/` | Mô hình bảng, trọng số GRU và thông số chuẩn hóa |
| `reports/` | Dự đoán kiểm thử, chỉ số, phân hoạch, thời gian và biểu đồ |
| `notebooks/01_eda.ipynb` | Notebook phân tích đã chạy |
| `docs/` | Báo cáo Word/Markdown/PDF, 20 slide, tài liệu kỹ thuật |
| `tests/` | Kiểm thử dữ liệu, mô hình, CSV và giao diện |

[Giải thích mã nguồn](docs/giai-thich-code.md) · [Nội dung trình bày](docs/noi-dung-trinh-bay.md) · [Danh mục bàn giao](docs/danh-muc-ban-giao.md)

Bản báo cáo dùng thông tin trường và GVHD theo phiếu đăng ký. Mẫu trình bày, số trang và thủ tục nộp cuối cùng phụ thuộc quy định khoa và xác nhận của giảng viên.

CSV đầu vào: tối đa 512 MiB, hỗ trợ `.csv` và `.csv.gz`, gồm tên cột gốc SDU. Chọn đúng giai đoạn sử dụng; chế độ Theo lô xử lý tới 2.000 chu kỳ. File lớn nhất của bộ hiện tại khoảng 82,8 MiB sau giải nén.

## Giám sát xu hướng bất thường

Trang **Xu hướng bất thường** hiển thị SOH tham chiếu, xu hướng từ lịch sử, điểm gắn cờ và lý do. Isolation Forest được kiểm thử giữ riêng pin; ngưỡng chỉ học từ train. Quy tắc nền dùng tối đa 8 khoảng quan sát trước đó. Chạy riêng:

```powershell
.\.venv\Scripts\python.exe scripts\analyze_anomalies.py
```

Cờ không phải xác nhận lỗi hoặc cảnh báo an toàn. Chưa có nhãn lỗi thực để tính precision/recall. Chức năng này chưa được kiểm chứng bằng nhãn lỗi thực tế trên xe; xem `docs/kiem-chung-bms.md`. Chức năng dùng SOH tham chiếu sau đo dung lượng, tách khỏi mô hình dự đoán 120 giây đầu.

## Phương án kết hợp trong khóa luận

**Ridge–RF hiệu chỉnh phần dư**: Ridge dự đoán nền, RF học phần dư trên tập học. Cùng 12 đặc trưng và 5 nhóm pin; không lấy nhãn test để hiệu chỉnh. Chạy riêng bằng `python scripts/evaluate_hybrid.py`. Mã mô hình ở `src/battery_soh/hybrid.py`, kết quả `reports/hybrid_*.csv`, mô hình bàn giao `artifacts/ridge_residual_forest.joblib`.

MAE 1,612 so với RF 1,619; RMSE 2,160 so với 2,157. Kết quả gần nhau, chưa đủ kết luận vượt trội. Đây là phương án kết hợp thuật toán có sẵn, không khẳng định thuật toán mới trong nghiên cứu. Chọn được trên trang Dự đoán SOH, mặc định vẫn là RF.

## Thực nghiệm bổ sung XJTU và báo cáo giữa kỳ (lưu trữ)

Nguồn [XJTU 2024](https://zenodo.org/records/10963339): Lishen 18650 NCM, 2 Ah, CC BY 4.0. Triển khai **23 pin Batch-1/2** trong tổng 55 pin của nguồn; các nhóm còn lại có quy trình khác nên chưa đưa vào thực nghiệm này. Đã tải nguyên gốc và kiểm tra nguồn của 23 MAT; xử lý 46.215.511 điểm đo, tạo 6.961 chu kỳ hợp lệ. Đánh giá chính dùng **6.938 chu kỳ**, không dùng 23 chu kỳ đầu xả 0,2C để tránh trộn với các chu kỳ xả 1C.

Bản thực nghiệm XJTU trước đây (hiện lưu trữ, đã thay bằng **BMS trên xe** trên giao diện): so sánh mô hình giữ riêng pin, kiểm thử chuyển miền/batch, biểu đồ theo pin, nguồn và dự đoán MAT riêng. Không đưa MAT XJTU vào bộ đọc CSV SDU. Mô hình XJTU dùng dòng chuẩn hóa theo 2 Ah và không dùng dung lượng đo/SOH làm đầu vào.

| Cấu hình trên pin XJTU giữ riêng | MAE (điểm % SOH) | RMSE |
| --- | ---: | ---: |
| Ridge | 0,971 | 1,205 |
| Random Forest | 0,577 | 0,764 |
| LightGBM | 0,596 | 0,787 |
| GRU | 1,240 | 1,543 |
| Ridge–RF phần dư | 0,666 | 0,828 |
| RF đa nguồn SDU + XJTU | 0,623 | 0,867 |

Năm vòng chia theo mã pin, cấu hình cố định. RF đa nguồn chưa cải thiện so với RF riêng XJTU trong cấu hình này. Chuyển mô hình chỉ học từ SDU sang XJTU có sai số lớn; ba đặc trưng chung nằm hoàn toàn ngoài khoảng SDU. Không suy rộng kết quả sang xe thực tế hoặc xem chênh lệch điểm giữa hai bộ là cải thiện trên cùng tập kiểm thử.

- [Thực nghiệm XJTU và cách chạy riêng](docs/thuc-nghiem-xjtu.md).
- [Dữ liệu, nguồn và cách tải lại](data/xjtu/README.md).
- [Notebook XJTU đã chạy](notebooks/03_thuc_nghiem_xjtu.ipynb).
- [Báo cáo giữa kỳ 10/11/2026 — Word](docs/bao-cao-giua-ky-10-11-2026.docx).
- [Slide giữa kỳ — 12 trang, có ghi chú trình bày](docs/slide-giua-ky-10-11-2026.pptx).

Gói sản phẩm kèm bảng dẫn xuất và mô hình đã huấn luyện; không kèm 722 MiB MAT gốc. Không cần tải MAT hoặc cài PyTorch để xem ứng dụng. Tải nguồn và chạy lại thực nghiệm đầy đủ bằng các script XJTU khi cần. Cả SDU và XJTU đều là dữ liệu tế bào trong phòng lab. Phần BMS trên xe đã được bổ sung riêng bên dưới, với nhãn suy ra thay vì RPT độc lập; RUL chưa triển khai.

## Bổ sung BMS trên xe thực tế

Giao diện bổ sung đã chuyển từ XJTU sang **BMS trên xe**: dữ liệu sạc qua CAN của 20 xe BAIC EU500 dùng pin CATL NCM 145 Ah, công bố bởi Deng và cộng sự (Applied Energy 2023, DOI 10.1016/j.apenergy.2023.120954). SDU vẫn là nguồn thực nghiệm chính. Các kết quả XJTU trong tài liệu phía trên thuộc thí nghiệm lab lưu trữ, không được gọi là BMS.

Nhãn BMS là **SOH suy ra từ dòng điện và SOC khi sạc**, không có phép đo dung lượng RPT độc lập. Mô hình BMS được học riêng và kiểm thử giữ riêng xe; không suy rộng thành kiểm chứng SOH vật lý, an toàn xe hoặc ứng dụng ở Việt Nam. Xem phương pháp, điều kiện loại phiên, nguồn và lệnh tái lập tại [Thực nghiệm BMS](docs/thuc-nghiem-bms.md).


## Thử nghiệm bổ sung CatBoost và XGBoost

Đã đánh giá bằng thư viện chính thức trên cùng 5 nhóm pin SDU; chọn cấu hình/số cây bằng validation giữ riêng pin trong train rồi refit đầy đủ trước khi test. CatBoost MAE 1,677 và XGBoost 1,692 điểm % SOH; chưa vượt Ridge–RF 1,612 hoặc RF 1,619 trong lần thử này. Giữ mô hình cũ làm mặc định. Có thể xem so sánh và chọn dự đoán hai mô hình bổ sung trong ứng dụng; cần `requirements-boosting.txt` trên máy cài mới. Chưa chạy thử nghiệm này trên BMS. [Nguồn, giao thức, kết quả và tái lập](docs/thuc-nghiem-boosting.md).


## Triển khai Render

Ứng dụng hiện dùng HTML/CSS/JavaScript và Flask; không chạy bằng Streamlit. Dùng [hướng dẫn Render](docs/render-deploy.md), cấu hình `render.yaml` và lệnh `python scripts/start_render.py`. Nhánh triển khai phải có đủ dữ liệu và mô hình; script build sẽ kiểm tra trước khi chạy.


## Sửa giao diện web

- `webapp/templates/index.html`: khung trang, tiêu đề tab và bản xem trước link.
- `webapp/static/app.css`: phông chữ, màu sắc, bố cục, giao diện điện thoại.
- `webapp/static/app.js`: điều hướng, biểu đồ, form CSV và lịch sử riêng theo tab.
- `webapp/server.py`: API tra cứu, kiểm tra dữ liệu và dự đoán bằng mô hình Python.
- `webapp/data.py`: đọc dữ liệu và tổng hợp kết quả kiểm thử đã có.

Sửa trong VS Code, kiểm tra rồi đẩy lên nhánh GitHub mà Render theo dõi. Link Render giữ nguyên sau triển khai. Thư mục `app/` được giữ làm bản tham chiếu và chứa các hàm dự đoán thuần Python; ứng dụng mới không tải trình chạy Streamlit. Thư viện nghiên cứu/báo cáo cài riêng từ `requirements-research.txt`.
