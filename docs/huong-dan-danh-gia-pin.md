# Đánh giá pin theo hồ sơ

Mở **Phân tích pin** để làm việc theo bốn bước. Công cụ dành cho người có dữ liệu đo, hỗ trợ phân tích và đối chiếu dung lượng; chưa chứng nhận lỗi, an toàn hoặc quyết định thay pin.

## 1. Chọn bài toán và khai báo hồ sơ

- **Tín hiệu đo:** pin khác hoặc chưa rõ cấu hình. Chỉ tổng hợp điện áp, dòng, nhiệt độ và điện lượng đoạn quan sát; không suy SOH từ đoạn sạc/xả.
- **SDU:** đầu xả cell SDU NMC 2,4 Ah, đúng phạm vi nguồn. Hỗ trợ Random Forest, Ridge–RF, CatBoost, XGBoost.
- **BAIC EU500:** đầu sạc bộ pin NMC 145 Ah, đúng quy ước BMS của nguồn. Hỗ trợ Random Forest và Ridge–RF. Nhãn SOH suy ra từ dòng/SOC, chưa có phép đo dung lượng RPT độc lập.
- **Dung lượng đo:** hai dung lượng xả đầy đủ của cùng pin và cùng điều kiện. SOH = hiện tại / tham chiếu × 100. Không dùng SOC hoặc lượng điện nạp của một phiên sạc dở dang.

Ghi mã pin/xe, ngày đo, hóa học, cấp đo, dung lượng định mức và điều kiện đo/thiết bị. Không lấy mẫu minh họa đã tham gia huấn luyện làm bằng chứng kiểm thử độc lập.

## 2. Tiếp nhận dữ liệu

CSV/CSV.GZ tối đa 512 MiB; JSON dạng mảng bản ghi phẳng tối đa 20 MiB. Mỗi hồ sơ chọn một pin, một chu kỳ và một giai đoạn, tối đa 100.000 dòng. File nhiều nhóm cần chọn cột và giá trị lọc. File lớn hơn nên tách theo pin/chu kỳ trước khi tải.

Với SDU/tín hiệu, xem trước năm dòng, chọn cột thời gian/điện áp/dòng/nhiệt độ, xác nhận đơn vị s/ms/min, V/mV, A/mA, °C/K và dấu dòng xả. Thời gian bắt đầu tại dòng đầu của đoạn được chọn; với SDU phải lấy đúng đầu xả. Đổi tên cột không chứng minh mô hình phù hợp.

BAIC cần tên cột và đơn vị của file mẫu: `time_s`, `soc`, `pack_voltage`, `charge_current`, `max_cell_voltage`, `min_cell_voltage`, `max_temperature`, `min_temperature`. Dòng sạc âm theo nguồn; cần đủ cửa sổ đầu sạc 120 giây.

## 3. Kiểm tra trước khi chạy

Bấm **Kiểm tra dữ liệu & phạm vi**. Chưa gọi mô hình ở bước này. Máy chủ kiểm tra lại khi bấm **Phân tích & lập báo cáo**, nên không thể bỏ qua bằng cách bỏ bước kiểm tra ở trình duyệt. Mọi thay đổi đầu vào làm mất kết quả kiểm tra và dự đoán cũ.

Sửa mục không đạt trước khi tiếp tục. Pin ngoài phạm vi SDU/BAIC chuyển sang phân tích tín hiệu hoặc phép đo dung lượng. Đặc trưng ngoài khoảng huấn luyện được ghi cảnh báo trong kết quả; chưa có khoảng dự đoán đã hiệu chuẩn riêng cho mỗi lần đo.

## 4. Kết quả, báo cáo và lịch sử

Kết quả có SOH (nếu phù hợp), mức chai, dung lượng, kiểm tra đầu vào, giải thích mô hình SDU, biểu đồ tín hiệu, bằng chứng kiểm thử và bước đối chiếu tiếp theo. SOH trên 100% không được đổi thành mức chai âm.

Tải CSV, JSON hoặc báo cáo HTML độc lập. Mở HTML và chọn **In / Lưu PDF** để có bản PDF; không cần dịch vụ xuất tài liệu bên ngoài. Báo cáo có mã hồ sơ, SHA256 file nguồn và mô hình, cấu hình, ngày đo, điều kiện đo và phiên bản ứng dụng.

Chọn **Lưu vào lịch sử** để giữ trong tab. Chỉ khi bật tùy chọn lưu trên thiết bị mới ghi vào localStorage; không đồng bộ tài khoản. Tối đa 100 hồ sơ mỗi nơi lưu. Trình duyệt có thể từ chối lưu, hết dung lượng hoặc xóa lịch sử; tự tải báo cáo để lưu trữ. Xóa từng hồ sơ tại **Hồ sơ & lịch sử**.

Chỉ tính chênh lệch khi cùng pin, bài toán, nguồn, cấu hình, phiên bản mô hình, giai đoạn, điều kiện và hai ngày đo khác nhau; phép đo dung lượng phải cùng mốc tham chiếu. Khác điều kiện chỉ hiển thị hai hồ sơ, không tính mức thay đổi. Hai lần đo không đủ để kết luận tốc độ suy giảm hoặc dự báo tuổi thọ.

Ứng dụng không lưu file và hồ sơ vào cơ sở dữ liệu máy chủ, không tự dùng upload để huấn luyện. Không đưa thông tin nhạy cảm vào tên file/URL. Cần một thiết kế tài khoản, quyền truy cập và lưu trữ bền vững riêng nếu triển khai quản lý đội xe nhiều người dùng.

## Kiểm thử và triển khai

Từ gốc kho, dùng Python 3.12 và môi trường đã cài `requirements-render.txt` cùng pytest:

```bash
.venv/bin/python -m pytest -q tests/test_assessment.py tests/test_web.py tests/test_focused_scope.py tests/test_bms_assessment.py
.venv/bin/python scripts/check_hosting.py
PORT=8504 .venv/bin/python scripts/start_render.py
```

Kiểm thử trình duyệt tùy chọn cần Node.js, Playwright và Chromium:

```bash
ASSESSMENT_BASE_URL=http://127.0.0.1:8504 node tests/browser_assessment.cjs
```

Có thể đặt `CHROMIUM_PATH` nếu Chromium không nằm tại `/usr/bin/chromium`. Bộ kiểm thử chạy dự đoán mẫu, upload và đổi đơn vị, tải báo cáo, vô hiệu kết quả cũ, lưu lịch sử, đối chiếu hai ngày và kiểm tra bố cục điện thoại.

Render tiếp tục dùng `requirements-render.txt`, `scripts/check_hosting.py` và `scripts/start_render.py`; không thêm phụ thuộc production. Sau triển khai, kiểm tra `/healthz`, `/api/readiness`, phiên bản commit ở chân trang và chạy thử một hồ sơ trên chính bản Render trước khi xác nhận Live. `/api/readiness` xác nhận sự hiện diện tài nguyên, không thay thế kiểm thử dự đoán.

Chưa bổ sung dữ liệu đo độc lập mới, chưa hiệu chuẩn khoảng dự đoán và chưa đưa Ridge/LightGBM/GRU vào API dự đoán trực tiếp. Các phần này cần thực nghiệm và kiểm chứng riêng.
