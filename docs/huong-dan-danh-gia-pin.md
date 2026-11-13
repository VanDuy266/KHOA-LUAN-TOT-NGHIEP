# Đánh giá pin theo hồ sơ

Mở **Phân tích pin**, chọn phép phân tích, nhập dữ liệu và nhấn **Phân tích**. Công cụ dành cho người có dữ liệu đo, hỗ trợ phân tích và đối chiếu dung lượng; chưa chứng nhận lỗi, an toàn hoặc quyết định thay pin.

## 1. Chọn bài toán và khai báo hồ sơ

- **Tín hiệu đo:** pin khác hoặc chưa rõ cấu hình. Chỉ tổng hợp điện áp, dòng, nhiệt độ và điện lượng đoạn quan sát; không suy SOH từ đoạn sạc/xả.
- **SDU:** đầu xả cell SDU NMC 2,4 Ah, đúng phạm vi nguồn. Hỗ trợ Random Forest, Ridge–RF, Ridge, LightGBM, CatBoost, XGBoost.
- **BAIC EU500:** đầu sạc bộ pin NMC 145 Ah, đúng quy ước BMS của nguồn. Hỗ trợ Random Forest và Ridge–RF. Nhãn SOH suy ra từ dòng/SOC, chưa có phép đo dung lượng RPT độc lập.
- **Dung lượng đo:** hai dung lượng xả đầy đủ của cùng pin và cùng điều kiện. SOH = hiện tại / tham chiếu × 100. Không dùng SOC hoặc lượng điện nạp của một phiên sạc dở dang.

Ghi mã pin/xe, ngày đo, hóa học, cấp đo, dung lượng định mức và điều kiện đo/thiết bị. Không lấy mẫu minh họa đã tham gia huấn luyện làm bằng chứng kiểm thử độc lập.

## 2. Tiếp nhận dữ liệu

CSV/CSV.GZ tối đa 512 MiB; JSON dạng mảng bản ghi phẳng tối đa 20 MiB. Mỗi hồ sơ chọn một pin, một chu kỳ và một giai đoạn, tối đa 100.000 dòng. File nhiều nhóm cần chọn cột và giá trị lọc. File lớn hơn nên tách theo pin/chu kỳ trước khi tải.

Với SDU/tín hiệu, xem trước năm dòng, chọn cột thời gian/điện áp/dòng/nhiệt độ, xác nhận đơn vị s/ms/min, V/mV, A/mA, °C/K và dấu dòng xả. Thời gian bắt đầu tại dòng đầu của đoạn được chọn; với SDU phải lấy đúng đầu xả. Đổi tên cột không chứng minh mô hình phù hợp.

BAIC cần tên cột và đơn vị của file mẫu: `time_s`, `soc`, `pack_voltage`, `charge_current`, `max_cell_voltage`, `min_cell_voltage`, `max_temperature`, `min_temperature`. Dòng sạc âm theo nguồn; cần đủ cửa sổ đầu sạc 120 giây.

## 3. Kiểm tra trước khi chạy

Nhấn **Phân tích**. Máy chủ kiểm tra dữ liệu và phạm vi trước khi gọi mô hình; dữ liệu không đạt được trả về kèm lỗi. Mọi thay đổi đầu vào làm mất kết quả kiểm tra và dự đoán cũ.

Sửa mục không đạt trước khi tiếp tục. Pin ngoài phạm vi SDU/BAIC chuyển sang phân tích tín hiệu hoặc phép đo dung lượng. Đặc trưng ngoài khoảng huấn luyện được ghi cảnh báo trong kết quả; chưa có khoảng dự đoán đã hiệu chuẩn riêng cho mỗi lần đo.

## 4. Kết quả, báo cáo và lịch sử

Kết quả có SOH (nếu phù hợp), mức chai, dung lượng, kiểm tra đầu vào, giải thích mô hình SDU, biểu đồ tín hiệu, bằng chứng kiểm thử và bước đối chiếu tiếp theo. SOH trên 100% không được đổi thành mức chai âm.

Tải CSV, JSON hoặc báo cáo HTML độc lập. Mở HTML và chọn **In / Lưu PDF** để có bản PDF; không cần dịch vụ xuất tài liệu bên ngoài. Báo cáo có mã hồ sơ, SHA256 file nguồn và mô hình, cấu hình, ngày đo, điều kiện đo và phiên bản ứng dụng.

Chọn **Lưu kết quả** để giữ trong tab. Chỉ khi bật tùy chọn lưu trên thiết bị mới ghi vào localStorage; không đồng bộ tài khoản. Tối đa 100 hồ sơ mỗi nơi lưu. Trình duyệt có thể từ chối lưu, hết dung lượng hoặc xóa lịch sử; tự tải báo cáo để lưu trữ. Xóa từng hồ sơ tại **Hồ sơ & lịch sử**.

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

Chưa bổ sung dữ liệu đo độc lập mới, chưa hiệu chuẩn khoảng dự đoán và chưa đưa GRU vào API dự đoán trực tiếp. Các phần này cần thực nghiệm và kiểm chứng riêng.

## Dữ liệu riêng: từ tín hiệu đến mô hình và dự đoán mới

Trang **Mô hình của tôi** hỗ trợ bảng của người dùng; không tra kết quả dự đoán từ báo cáo SDU đã lưu.

1. Nếu có tín hiệu thô, xuất CSV chuẩn hóa gồm `battery, cycle, phase_code, time, terminal_voltage, terminal_current, temperature`; tùy chọn nhãn `soh_pct` nhất quán trong mỗi nhóm. Công cụ trích xuất thống kê từ 120 giây đầu từng nhóm. Giữ đúng đơn vị V/A/°C, cùng cách lấy cửa sổ và quy trình ở cả train lẫn dữ liệu mới.
2. Nếu chưa có nhãn, chỉ tạo bảng đặc trưng để dự đoán bằng mô hình phù hợp. Muốn huấn luyện cần nhãn từ phép đo/nguồn đã giải thích; ứng dụng không tự tạo nhãn giả từ dự đoán cũ.
3. Tải bảng có nhãn tại **Huấn luyện trên dữ liệu của tôi**, ghi nguồn nhãn; cần 40–5.000 dòng, 4–200 pin, mỗi pin tối thiểu 5 mẫu. Các pin test được giữ riêng khỏi train. Chỉ số MAE/RMSE/R² được tính lại từ file tải lên.
4. Bật xuất mô hình dùng lại, ghi hóa học, cấp đo, chế độ, dung lượng định mức và quy trình trích xuất. Tải `ridge_portable.json` hoặc bấm **Dự đoán dữ liệu mới**. Mô hình Ridge này chỉ học nhóm train; không refit theo nhãn test.
5. Tải CSV mới gồm `battery` và 12 đặc trưng, không cần `soh_pct`; khai báo đúng cấu hình/quy trình và xác nhận. Server tính lại dự đoán từ tham số JSON và file mới. Kết quả nêu mã pin có trong train hay không, số đặc trưng ngoài miền học và SHA256 file/mô hình.

Không nạp file joblib/pickle của người dùng để suy luận. JSON chỉ chứa tham số số học, vẫn không xác thực được chất lượng nhãn hoặc nguồn gốc mô hình. Kết quả là thực nghiệm trong cấu hình khai báo; cùng cấu hình chưa chứng minh tổng quát hóa, không chứng nhận lỗi/an toàn.

## Sao lưu và xu hướng theo hồ sơ thực tế

Tại **Hồ sơ & lịch sử**, tải gói JSON để sao lưu/chuyển thiết bị; nhập một hồ sơ hoặc gói tối đa 5 MiB. Server kiểm tra cấu trúc, số hữu hạn và giới hạn kích thước, rồi tạo lại báo cáo. Hồ sơ nhập luôn được gắn cờ chưa xác thực. Mã đã tồn tại được bỏ qua; không ghi đè âm thầm. Thao tác nhập không lưu hồ sơ trên server.

Chọn ít nhất 5 hồ sơ khác ngày, cùng pin, mô hình, nguồn, giai đoạn, mốc tham chiếu và điều kiện để phân tích xu hướng theo ngày. Không biến nhiều lần chạy cùng ngày thành nhiều mốc đo. Kết quả chỉ ngoại suy khi xu hướng giảm đủ rõ và ngưỡng nằm trong giới hạn của phương pháp; không phải dự báo ngày hỏng.

## Phiên bản giao diện mới

Trang chính là biểu mẫu **Phân tích pin**, dùng một nút chạy. Các thông số ít dùng được gấp lại; huấn luyện, so sánh và mô hình riêng nằm trong menu **Nghiên cứu**. Cuối trang hiển thị phiên bản sản phẩm **V2.0**. Mã commit và trạng thái tài nguyên chỉ dùng cho chẩn đoán qua API.

API dự đoán SDU hiện hỗ trợ thêm Ridge và LightGBM, tổng cộng sáu mô hình bảng; LightGBM dùng đóng góp TreeSHAP gốc, Ridge dùng hệ số trên đặc trưng chuẩn hóa. GRU vẫn phục vụ thực nghiệm chuỗi, chưa đưa vào dịch vụ dự đoán trực tiếp trên Render.

Kiểm thử mở rộng:

```bash
.venv/bin/python -m pytest -q tests/test_records.py tests/test_custom_model.py tests/test_assessment.py tests/test_training.py
npm ci --prefix tests
# Nếu chưa có Chromium:
tests/node_modules/.bin/playwright install chromium
ASSESSMENT_BASE_URL=http://127.0.0.1:8504 node tests/browser_workbench.cjs
```

GitHub Actions tại `.github/workflows/web-validation.yml` chạy kiểm tra tài nguyên, bộ kiểm thử ứng dụng và hai luồng trình duyệt khi push/PR. Đây là bộ kiểm thử ứng dụng, không tái huấn luyện toàn bộ thực nghiệm nghiên cứu hoặc thu thập thêm dữ liệu đo độc lập.

## Giao diện gọn

Menu chính gồm Phân tích pin và Lịch sử. Thông số bổ sung, dữ liệu mẫu và các công cụ nghiên cứu được gấp lại. Khi có kết quả, dùng Sửa dữ liệu để quay lại biểu mẫu hoặc Phân tích khác để bắt đầu hồ sơ mới. Icon chức năng được giữ; bỏ các thẻ giới thiệu và nhãn trang trí.

## Nhận diện dữ liệu đầu vào

Tên cột tiếng Việt có dấu/không dấu và đơn vị ghi trong tiêu đề được gợi ý tự động. Nếu một tín hiệu khớp nhiều cột, cần chọn rõ cột; không tự chọn cột đầu tiên. Tên cột không có đơn vị dùng đơn vị chuẩn đang hiển thị, có thể sửa trong mục Cột và đơn vị. Tên pin được lấy từ mã pin trong bản xem trước hoặc tên tệp khi chưa nhập; toàn bộ tệp vẫn phải qua kiểm tra nhóm trước phân tích.

Nút Xem kết quả mẫu chạy trực tiếp một ví dụ được ghi nhãn mẫu. Khi nhập dung lượng, chỉ dùng hai phép đo đầy đủ cùng điều kiện, không dùng SOC. Kết quả có phần diễn giải tỷ lệ dung lượng và biểu đồ đổi được tín hiệu hiển thị.

## Bộ lọc nhóm và kiểm tra nguồn

Danh sách cột lọc chỉ chứa cột đúng nghĩa. `Cycle_Index` là chu kỳ; `Step_Index` là bước đo trong chu kỳ. Điện áp/dòng điện không được chọn làm giai đoạn sử dụng. Không có cột tương ứng thì bộ lọc đó không xuất hiện. Với BAIC, các nhóm là xe và phiên sạc.

Tệp thiếu cấu trúc tám tín hiệu BAIC sẽ bị chặn trước khi lọc hoặc dự đoán; có thể chuyển sang xem số đo mà không suy SOH. Khi không có dòng khớp, thông báo nêu bộ lọc đã dùng và một số giá trị thực quan sát được. Không tự bỏ bộ lọc để ép ra kết quả.

Với tệp SDU gốc dùng `Test_Time(s)`, sau khi chọn một chu kỳ, hệ thống lấy 120 giây đầu có dòng xả âm, không lấy nhầm 120 giây đầu của bước sạc. Nếu lọc riêng một bước sạc, yêu cầu bị từ chối thay vì bỏ qua bộ lọc.
