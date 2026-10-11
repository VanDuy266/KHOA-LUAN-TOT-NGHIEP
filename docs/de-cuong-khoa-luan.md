# Đề cương triển khai khóa luận khoa học dữ liệu

## Đề tài theo phiếu đăng ký

**Phân tích và dự đoán tình trạng sức khỏe pin xe điện bằng các mô hình học máy.**

Đây là đề cương đề xuất để trao đổi với giảng viên, chưa phải báo cáo kết quả nghiên cứu. Phiếu đăng ký chỉ xác định tên đề tài; không quy định bộ dữ liệu, mô hình hay tiêu chí nghiệm thu.

## 1. Mục tiêu và câu hỏi nghiên cứu

- Phân tích sự suy giảm dung lượng pin theo chu kỳ sử dụng.
- Dự đoán trạng thái sức khỏe pin (State of Health, SOH) từ thông tin đo được ở chu kỳ hiện tại hoặc trước đó.
- So sánh mô hình cơ sở với các mô hình học máy trên cùng tập đánh giá.
- Xác định đặc trưng có ích và phân tích các trường hợp dự đoán sai.

Câu hỏi chính: mô hình học máy có cải thiện sai số dự đoán SOH so với mô hình cơ sở khi đánh giá trên một pin chưa dùng trong huấn luyện không?

## 2. Phạm vi

Ưu tiên bài toán hồi quy SOH; dự đoán tuổi thọ còn lại (RUL) là phần mở rộng nếu dữ liệu và thời gian cho phép. Không đồng nhất SOH với mức sạc SOC.

Định nghĩa mục tiêu dự kiến: `SOH (%) = 100 × dung lượng xả đo được / dung lượng tham chiếu`. Chọn dung lượng danh định hoặc dung lượng ban đầu theo tài liệu của bộ dữ liệu, ghi rõ cách xác định và áp dụng nhất quán cho từng pin.

Dữ liệu thử nghiệm trên cell lithium-ion có thể dùng để nghiên cứu phương pháp liên quan đến pin xe điện. Kết quả trên cell trong phòng thí nghiệm không đủ để khẳng định hiệu quả trên bộ pin xe điện vận hành thực tế; cần nêu rõ giới hạn này trong báo cáo.

## 3. Dữ liệu

Ứng viên cần kiểm tra: dữ liệu lão hóa pin NASA hoặc CALCE. Trước khi chọn phải xác minh nguồn tải chính thức, quyền sử dụng, tài liệu đo, số pin, số chu kỳ và khả năng truy cập. Chưa tải hoặc xác nhận bộ dữ liệu trong bước lập đề cương này.

Ưu tiên dữ liệu có mã pin, mã chu kỳ, thời gian, điện áp, dòng điện, nhiệt độ và dung lượng xả. Lưu dữ liệu gốc riêng, không chỉnh sửa trực tiếp; ghi nguồn, ngày tải và checksum. Nếu dữ liệu có ít pin, giới hạn sức mạnh của kết luận và báo cáo sai số theo từng pin.

## 4. Quy trình xử lý và đặc trưng

1. Đọc dữ liệu; kiểm tra đơn vị, cấu trúc chu kỳ, thiếu dữ liệu, bản ghi trùng và thứ tự thời gian.
2. Xác định chu kỳ sạc/xả hợp lệ và xây dựng nhãn SOH.
3. Khảo sát đường cong điện áp, dòng, nhiệt độ và suy giảm dung lượng theo từng pin.
4. Trích xuất đặc trưng từ cửa sổ đo đã xác định: thống kê điện áp/dòng/nhiệt độ, thời gian sạc hoặc xả, độ dốc đường cong và đặc trưng lịch sử chỉ dùng các chu kỳ đã xảy ra.
5. Huấn luyện và đánh giá bằng pipeline có thể chạy lại.

Phải xác định thời điểm có thể đưa ra dự đoán. Nếu đặc trưng cần toàn bộ chu kỳ xả, mô hình chỉ ước lượng SOH sau chu kỳ đó, không phải dự báo trước chu kỳ.

Không dùng dung lượng xả của chu kỳ mục tiêu, SOH mục tiêu hoặc biến suy ra trực tiếp từ chúng làm đầu vào. Đặc trưng tích phân dòng điện trên toàn bộ chu kỳ xả có thể tái tạo dung lượng mục tiêu; cần loại bỏ hoặc phân tích rõ nguy cơ rò rỉ. Không dùng dữ liệu chu kỳ tương lai để tính đặc trưng lịch sử.

## 5. Mô hình và thiết kế thực nghiệm

- Cơ sở: dự đoán SOH trung bình của tập huấn luyện và hồi quy theo chỉ số chu kỳ.
- Mô hình so sánh: Ridge, Random Forest và một mô hình boosting như HistGradientBoosting hoặc XGBoost.
- Chỉ cân nhắc LSTM khi có đủ dữ liệu chuỗi và kết quả cơ sở đã được kiểm chứng.

Đánh giá chính: chia nhóm theo mã pin hoặc leave-one-battery-out. Trong từng vòng đánh giá, chọn siêu tham số bằng dữ liệu huấn luyện; không dùng pin kiểm thử để chọn đặc trưng hoặc tham số. Các bước điền thiếu, chuẩn hóa và lựa chọn đặc trưng chỉ fit trên phần huấn luyện.

Đánh giá bổ sung: chia theo thời gian để đo khả năng dự đoán các chu kỳ về sau trên pin đã quan sát. Báo cáo riêng vì đây là câu hỏi khác với tổng quát hóa sang pin mới. Không chia ngẫu nhiên các chu kỳ của cùng pin rồi dùng kết quả đó để khẳng định khả năng tổng quát hóa.

Chỉ số chính: MAE và RMSE theo điểm phần trăm SOH; R² là chỉ số bổ sung. Trình bày kết quả theo từng pin và trung bình giữa các pin, số mẫu, sơ đồ chia tập, seed và siêu tham số. So sánh bỏ từng nhóm đặc trưng nếu thời gian cho phép. Chưa có số liệu thực nghiệm; không điền kết quả giả định.

## 6. Sản phẩm dự kiến

- Mã tải/đọc dữ liệu và kiểm tra chất lượng dữ liệu.
- Notebook phân tích khám phá có biểu đồ và diễn giải.
- Pipeline trích xuất đặc trưng, huấn luyện và đánh giá.
- Bảng kết quả, biểu đồ SOH thực tế/dự đoán và phân tích lỗi.
- Demo Streamlit nhận dữ liệu đúng định dạng, trả dự đoán kèm phạm vi áp dụng; thực hiện sau khi mô hình đã được đánh giá.
- Báo cáo khóa luận, slide và hướng dẫn tái lập thực nghiệm.

Cấu trúc dự kiến: `data/`, `notebooks/`, `src/`, `configs/`, `reports/`, `app/`, `tests/`. Chỉ tạo khai báo phụ thuộc và lệnh chạy khi đã chọn bộ dữ liệu và triển khai mã tương ứng.

## 7. Khung báo cáo

1. Giới thiệu: bài toán, mục tiêu, phạm vi và đóng góp.
2. Cơ sở lý thuyết và nghiên cứu liên quan: pin lithium-ion, SOH, học máy và phương pháp đánh giá.
3. Dữ liệu và phương pháp: nguồn dữ liệu, làm sạch, đặc trưng, mô hình, phòng tránh rò rỉ.
4. Thực nghiệm: cấu hình, kết quả thực đo, so sánh và phân tích lỗi.
5. Kết luận: kết quả được chứng minh, hạn chế và hướng phát triển.

Các nhận định khoa học cần trích dẫn nguồn đã đọc và kiểm chứng. Không tạo tài liệu tham khảo hoặc kết quả thực nghiệm giả.

## 8. Lộ trình đề xuất

| Giai đoạn | Công việc | Điều kiện hoàn thành |
| --- | --- | --- |
| 1 | Chốt dữ liệu và định nghĩa SOH | Đọc được dữ liệu, xác minh đơn vị và nhãn |
| 2 | Làm sạch và khám phá dữ liệu | Có báo cáo chất lượng và biểu đồ theo pin |
| 3 | Đặc trưng và mô hình cơ sở | Pipeline chạy lại được, không dùng thông tin tương lai |
| 4 | So sánh mô hình | Có đánh giá theo nhóm pin và kết quả thực đo |
| 5 | Phân tích lỗi và demo | Demo dùng đúng pipeline đã đánh giá |
| 6 | Hoàn thiện báo cáo và slide | Mọi bảng kết quả truy được về lần chạy thực nghiệm |

## 9. Thông tin cần bổ sung

- Bộ dữ liệu có sẵn hoặc cho phép sử dụng dữ liệu công khai.
- Thời hạn, mẫu báo cáo và yêu cầu của giảng viên.
- Phạm vi mong muốn: nghiên cứu SOH, RUL bổ sung hay ứng dụng minh họa.

Bước tiếp theo mặc định là xác minh một bộ dữ liệu công khai phù hợp, rồi triển khai pipeline SOH và đánh giá mô hình cơ sở trước khi xây dựng demo.
