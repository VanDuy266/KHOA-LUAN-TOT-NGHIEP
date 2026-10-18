# Giải thích code dành cho sinh viên

## Chọn công nghệ

Python 3.12 phù hợp vì có thư viện xử lý dữ liệu và học máy phổ biến. `pandas` thao tác bảng, `NumPy` tính thống kê, `scipy.io.loadmat` đọc MATLAB, `scikit-learn` cung cấp mô hình và chỉ số, `matplotlib` vẽ kết quả. `Streamlit` tạo giao diện bằng Python, không cần làm thêm backend Java hoặc frontend JavaScript. Word và PowerPoint chỉ là phần xuất tài liệu, không cần cài để chạy dự đoán.

Code cố ý dùng hàm và vòng lặp thông thường. Không có mô hình mạng sâu tự viết, hệ thống agent, API AI hay framework triển khai phân tán. Không cần tự viết Random Forest: phần sinh viên cần hiểu là dữ liệu, cách tạo đặc trưng, cách gọi fit/predict và cách đánh giá.

## Luồng chạy

`MATLAB → bảng sạc/xả → làm sạch → bảng đặc trưng từng chu kỳ → chia theo pin → fit trên train → predict trên test → tính sai số → fit lại mô hình demo → giao diện`.

### Bước 1 — download_data.py

Đọc `data/manifest.json`; mỗi file có URL và SHA-256. Nếu đã có file, kiểm tra checksum; nếu chưa có, tải bằng HTTPS. Khi checksum sai thì dừng. Không tự đổi checksum để chấp nhận file khác.

### Bước 2 — prepare_data.py

`read_battery` lấy mảng operation trong MATLAB. Với từng operation, xem đó là sạc hay xả; tạo DataFrame từ time, điện áp, dòng và nhiệt độ. Mã pin, loại operation và chỉ số operation được thêm để giữ nguồn gốc từng dòng.

`clean_battery` loại dòng thiếu/vô hạn, loại trùng hoàn toàn nếu có và từ chối khóa thời gian xung đột. Trong dữ liệu thật chỉ có 2 dòng sạc B0018 thiếu tín hiệu. Sau xử lý còn 2.089.048 dòng; không có dữ liệu được nội suy hoặc tạo ngẫu nhiên.

Bảng toàn bộ phép đo không có nhãn SOH. Bảng xả có dung lượng vì file MATLAB đo capacity ở cuối chu kỳ xả. Không dùng capacity của một chu kỳ xả để tự gán nhãn cho mọi dòng sạc trước nó.

### Bước 3 — features.py

`validate_target` xác nhận nhãn của cùng một chu kỳ nhất quán và SOH = capacity / 2 Ah. `extract_window` chỉ lấy các mẫu trong 120 giây đầu và chọn mẫu đang xả có dòng < -0,1 A. Hàm tính mean, min, max, std và slope tùy nhóm tín hiệu.

Một chu kỳ có nhiều dòng đo nhưng chỉ có một nhãn SOH. Vì vậy 185.721 dòng xả tạo 636 mẫu mô hình, không phải 185.721 mẫu độc lập. Bốn nhóm pin vẫn là bốn cell bất kể số thời điểm đo.

### Bước 4 — run_experiment.py

`models()` tạo các mô hình có sẵn từ scikit-learn. `LeaveOneGroupOut` chia theo cột battery. Ở mỗi vòng, code lấy các chỉ số train/test, gọi `model.fit(X_train, y_train)` và `model.predict(X_test)`, rồi tính MAE/RMSE/R².

Không chuẩn hóa bằng toàn bộ dữ liệu rồi mới chia: StandardScaler nằm trong Pipeline nên fit cùng model trên train. RF và boosting không cần chuẩn hóa trong cấu hình này. Các tham số được giữ cố định, không thử nhiều giá trị rồi chọn theo test.

Sau đánh giá, RF được fit lại bằng cả 636 mẫu để tạo model demo. Mô hình này không được dùng để tạo điểm kiểm thử đã báo cáo. Hai việc "đánh giá" và "fit lại để sử dụng" phải được giải thích rõ khi bảo vệ.

### Bước 5 — analyze_results.py

Thử bỏ số chu kỳ hoặc nhiệt độ để quan sát thay đổi. Đây là phân tích bổ sung sau kết quả chính, không phải bằng chứng rằng nhóm đặc trưng nào không có giá trị trong mọi dữ liệu.

Thiết kế theo thời gian dùng 70% đầu một pin để học, 30% sau để test. Baseline dùng SOH cuối cùng đã biết trong train. RF không hơn baseline này trên dữ liệu hiện tại; cần báo cáo thật vì bài toán ngoại suy tương lai khác với ước lượng trên pin mới.

### Bước 6 — streamlit_app.py và các màn hình

File chính chỉ kiểm tra dữ liệu, nạp CSS, tạo thanh điều hướng và gọi màn hình được chọn. Mỗi màn hình có hàm `render()` trong `app/screens`, không dùng hệ thống class phức tạp:

- `overview.py`: số liệu tổng quan và hồ sơ Nguyễn Văn Duy, MSSV 2311553949, Khoa Học Dữ Liệu.
- `explorer.py`: lọc pin/chu kỳ, tra cứu tín hiệu thật, xuất CSV.
- `evaluation.py`: chọn mô hình, xem MAE/RMSE/R² và dự đoán trên pin giữ riêng.
- `forecast.py`: nhập CSV, nhận kết quả, lưu tạm trong phiên để tải file không làm mất kết quả.
- `profile.py`: nguồn dữ liệu, thuật ngữ và tài liệu.

`app/charts.py` gọi Altair để tạo biểu đồ. `app/labels.py` ánh xạ tên cột sang tiếng Việt trên một bản sao; không đổi tên cột trong pipeline tính toán. `app/app_data.py` dùng cache theo thời điểm sửa file để tránh đọc lại 185.721 dòng mỗi khi bấm bộ lọc. Dữ liệu upload không nằm trong cache dùng chung và không được thêm vào dữ liệu huấn luyện.

`app/prediction.py` kiểm tra CSV một pin/một chu kỳ, quy đổi tên cột tiếng Việt nếu có rồi gọi `extract_window` dùng chung với train. Khi đầu vào thay đổi, giao diện không hiển thị nhầm kết quả cũ. Mẫu B0005 đã nằm trong train demo nên không dùng kết quả đó làm điểm kiểm thử.

`app/styles.css` chỉ tạo màu sắc, khoảng cách và hiệu ứng nhẹ, không tham gia tính SOH. `.streamlit/config.toml` quy định theme sáng và giới hạn upload.

## Những chỗ có thể chỉnh để học

- Đọc `FEATURES` để biết chính xác đầu vào; không thêm capacity/SOH vào đó.
- Đọc `models()` để hiểu tham số; thay đổi tham số thì phải chạy lại và ghi nhận đây là thử nghiệm tiếp nối.
- Đọc `data/README.md` trước khi đổi đơn vị hoặc nguồn dữ liệu.
- Thêm pin phải có metadata, nguồn và checksum; không chỉ copy cùng pin rồi đổi mã.
- Học cách đọc những trường hợp model sai thay vì chỉ chọn biểu đồ đẹp.

## Lỗi Windows thường gặp

- Thiếu Python: kiểm tra `py -3.12 --version` trước khi tạo `.venv`.
- Đang đứng trong `app`: quay ra thư mục có README trước khi chạy.
- `No module named streamlit`: cài thư viện chưa xong hoặc dùng nhầm Python; dùng đúng `.venv\Scripts\python.exe`.
- `Operation cancelled by user`: chạy lại pip và đợi kết thúc; không tạo lại toàn bộ môi trường chỉ vì cài bị hủy.
- Lỗi checksum: giữ file và kiểm tra nguồn, không xóa bước xác minh.
- Cổng đang bận: dừng ứng dụng cũ hoặc thêm `--server.port=8502` khi chạy trên máy cá nhân.

## Điều cần tự giải thích khi bảo vệ

Định nghĩa SOH; lý do dùng 120 giây; khác nhau giữa dòng đo và mẫu nhãn; lý do giữ riêng pin; tại sao không dùng capacity làm đầu vào; MAE có đơn vị gì; tại sao RF chưa dự đoán được tuổi thọ còn lại; giới hạn bốn pin và dữ liệu không phải Việt Nam. Nguồn hỗ trợ và mã thư viện cần được ghi nhận theo quy định của trường, không dùng cách trình bày để che giấu quá trình thực hiện.
