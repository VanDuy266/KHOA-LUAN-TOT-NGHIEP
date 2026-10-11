# PHÂN TÍCH VÀ DỰ ĐOÁN TÌNH TRẠNG SỨC KHỎE PIN XE ĐIỆN BẰNG CÁC MÔ HÌNH HỌC MÁY

Trường Đại học Nguyễn Tất Thành — Khoa Công nghệ thông tin

Sinh viên: Nguyễn Văn Duy — MSSV: 2311553949 — Lớp: 23DTH2A

Giảng viên hướng dẫn theo phiếu đăng ký: ThS. Vương Xuân Chí

**Bản báo cáo nghiên cứu để trao đổi với giảng viên. Chưa được nghiệm thu, chưa áp dụng mẫu trình bày chính thức của trường.** Không có chữ ký, nhận xét hoặc cam kết được tạo thay cho sinh viên và giảng viên.

## Tóm tắt

Nghiên cứu xây dựng một quy trình ước lượng trạng thái sức khỏe (SOH) của cell lithium-ion từ tín hiệu điện áp, dòng điện và nhiệt độ trong 120 giây đầu chu kỳ xả. Dữ liệu sử dụng là bản CSV chuyển đổi công khai có dẫn nguồn NASA, được ghim tại một commit và kiểm tra SHA-256. Thực nghiệm chính gồm 468 chu kỳ của ba pin B05, B07 và B18. Các mô hình được so sánh bằng leave-one-battery-out để bảo đảm pin kiểm thử không xuất hiện trong huấn luyện. Random Forest đạt MAE trung bình giữa các pin là 1,241 điểm phần trăm SOH, so với 4,392 của hồi quy Ridge chỉ dùng chỉ số chu kỳ. Đây là kết quả trên bản chuyển đổi cộng đồng; chưa đối chiếu dữ liệu MAT gốc và chưa chứng minh khả năng áp dụng cho bộ pin xe điện thực tế.

Từ khóa: pin lithium-ion, SOH, hồi quy, Random Forest, đánh giá theo nhóm, khoa học dữ liệu.

## Chương 1. Giới thiệu

### 1.1. Bài toán nghiên cứu

Tình trạng sức khỏe của pin phản ánh sự suy giảm khả năng lưu trữ hoặc cung cấp năng lượng so với một trạng thái tham chiếu. Trong nghiên cứu này, SOH được định nghĩa theo dung lượng xả. SOH khác với trạng thái sạc SOC: một cell có thể được sạc đầy nhưng dung lượng tối đa đã giảm so với danh định.

Đo toàn bộ dung lượng xả cung cấp nhãn tham chiếu cho SOH nhưng cần quan sát hết chu kỳ. Nghiên cứu đặt câu hỏi liệu một cửa sổ tín hiệu ngắn ở đầu chu kỳ có đủ thông tin để ước lượng SOH hay không. Thời điểm đưa ra dự đoán là sau 120 giây kể từ mốc bắt đầu bản ghi chu kỳ; đây không phải dự báo SOH trước khi bắt đầu xả hoặc dự đoán tuổi thọ còn lại.

### 1.2. Mục tiêu

- Xây dựng quy trình tải dữ liệu có kiểm tra tính toàn vẹn và ghi nguồn.
- Kiểm tra cấu trúc chu kỳ, tính nhất quán nhãn và điều kiện cửa sổ quan sát.
- So sánh mô hình cơ sở, hồi quy tuyến tính có điều chuẩn và mô hình cây.
- Đánh giá trên pin chưa xuất hiện trong huấn luyện; báo cáo kết quả theo từng pin.
- Cung cấp ứng dụng minh họa và các bước tái lập thực nghiệm.

### 1.3. Phạm vi và đóng góp

Phạm vi chính là hồi quy SOH trên ba cell lithium-ion trong dữ liệu đã chuyển đổi. Không có dữ liệu vận hành xe điện, thông tin bộ pin, cân bằng cell hoặc quy trình đo thực địa. Không triển khai RUL, SOC hay quyết định thay pin vì chúng cần thiết kế và nhãn khác.

Đóng góp thực hiện gồm bộ kiểm tra dữ liệu, đặc trưng giới hạn theo thời gian, thiết kế đánh giá theo pin, các tệp dự đoán kiểm thử có thể kiểm tra lại và demo sử dụng cùng mã trích xuất đặc trưng. Nghiên cứu không tuyên bố đề xuất một thuật toán mới hoặc vượt mọi công trình trước đó.

## Chương 2. Cơ sở phương pháp

### 2.1. Định nghĩa SOH

Trong pipeline, dung lượng danh định là 2 Ah và SOH (%) = 100 × capacity / 2. Giá trị này phù hợp với quan hệ số học giữa hai cột capacity và SOH của bản CSV. Đó là xác nhận nội bộ của dữ liệu chuyển đổi; cần kiểm tra tài liệu thí nghiệm gốc trước khi coi 2 Ah là thông số được xác nhận độc lập.

Mỗi chu kỳ phải có nhãn dung lượng và SOH hữu hạn, nhất quán trong sai số 10⁻⁶. Nhãn chỉ được dùng làm biến đích. Không dùng capacity, SOH hoặc tích phân dòng điện toàn chu kỳ làm đặc trưng vì chúng có thể tái tạo trực tiếp biến đích.

### 2.2. Các mô hình

Mean baseline dự đoán trung bình SOH của tập huấn luyện. Cycle Ridge dùng số chu kỳ để mô hình hóa xu hướng suy giảm chung. Signal Ridge dùng toàn bộ đặc trưng sau chuẩn hóa và điều chuẩn L2; hệ số điều chuẩn khác nhau được cố định trước khi chạy.

Random Forest tổng hợp nhiều cây hồi quy, có thể biểu diễn quan hệ phi tuyến giữa tín hiệu và SOH. HistGradientBoosting xây dựng mô hình cộng dồn bằng cây, sử dụng biểu diễn histogram. Thực nghiệm giới hạn độ phức tạp và cố định random seed để chạy lại; không thực hiện tìm kiếm siêu tham số.

### 2.3. Đánh giá và rò rỉ dữ liệu

Các chu kỳ của cùng pin có tương quan và xu hướng suy giảm liên tiếp. Chia ngẫu nhiên từng chu kỳ có thể cho mô hình quan sát cùng pin ở cả hai tập, nên không trả lời được câu hỏi tổng quát hóa sang pin khác. Leave-one-battery-out tạo ba vòng: giữ B05, B07 hoặc B18 làm kiểm thử, dùng hai pin còn lại để huấn luyện.

Chuẩn hóa chỉ fit trên dữ liệu huấn luyện trong Pipeline. Các tham số cố định không được điều chỉnh theo kết quả kiểm thử. Demo chọn Random Forest trước khi xem điểm số. Nếu sau này chọn mô hình tốt nhất hoặc điều chỉnh đặc trưng dựa trên các kết quả hiện tại, cần tập đánh giá độc lập hoặc thiết kế nested validation để tránh đánh giá quá lạc quan.

### 2.4. Chỉ số

MAE là trung bình trị tuyệt đối của sai số; RMSE là căn bậc hai của trung bình bình phương sai số. Vì nhãn nằm trên thang 0–100, đơn vị của MAE/RMSE là điểm phần trăm SOH, không phải phần trăm sai số tương đối. R² so sánh tổng bình phương sai số với độ biến thiên của nhãn kiểm thử; R² có thể âm.

Kết quả tổng hợp lấy trung bình không trọng số giữa ba pin, không lấy trung bình tất cả chu kỳ. Cách này cho mỗi pin trọng số bằng nhau dù số chu kỳ khác nhau. Trung bình R² giữa các pin không phải R² tính trên dữ liệu gộp.

## Chương 3. Dữ liệu và triển khai

### 3.1. Nguồn và tính toàn vẹn

Nguồn tải thực tế là repository `standing-o/SoH_estimation_of_Lithium-ion_battery`, commit `f75a9dcb0a38244225b5807722ceac39e0cb4a20`. README của nguồn dẫn NASA Prognostic Center. Dự án lưu nguyên giấy phép MIT của repository nguồn, đường dẫn từng file và checksum trong manifest. Không tái sử dụng mã mô hình hoặc kết quả nghiên cứu của nguồn để trình bày như kết quả của dự án này.

Tám CSV được tải và kiểm tra checksum. Ba pin B05/B07/B18 được chọn cho thực nghiệm chính sau kiểm kê chất lượng và trước khi chạy mô hình. Năm pin còn lại chỉ xuất hiện trong bảng kiểm kê: B33 có SOH giảm tới khoảng 3,42%, B34 tới 37,30%; B46/B47/B48 có chu kỳ dung lượng bằng 0. Chưa có tài liệu gốc để giải thích các giá trị đó nên không đưa chúng vào kết luận chính. Đây là lựa chọn phạm vi cần trình bày minh bạch, không phải loại ngoại lai để nâng điểm số sau khi xem kết quả.

| battery | rows | cycles | missing_values | min_soh_pct | max_soh_pct | zero_capacity_cycles | primary |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B05 | 50285 | 168 | 0 | 64.373 | 92.824 | 0 | True |
| B07 | 50285 | 168 | 0 | 70.023 | 94.553 | 0 | True |
| B18 | 34866 | 132 | 0 | 67.053 | 92.750 | 0 | True |
| B33 | 47065 | 197 | 0 | 3.421 | 94.257 | 0 | False |
| B34 | 47065 | 197 | 0 | 37.297 | 91.015 | 0 | False |
| B46 | 24519 | 72 | 0 | 0.000 | 86.412 | 3 | False |
| B47 | 24519 | 72 | 0 | 0.000 | 83.715 | 3 | False |
| B48 | 24519 | 72 | 0 | 0.000 | 82.900 | 3 | False |

Trong dữ liệu chuyển đổi, B05/B07 có cùng toàn bộ trục thời gian; B33/B34 và B46/B47 cũng có hiện tượng tương tự. Điện áp, dòng và nhiệt độ không trùng toàn bộ. Hiện tượng này có thể liên quan cách chuyển đổi hoặc thí nghiệm, nhưng chưa đủ bằng chứng để xác định nguyên nhân. Do đó, đặc trưng độ dốc theo thời gian và đánh giá hiện tại phải được xác nhận lại từ dữ liệu gốc.

### 3.2. Kiểm tra và đặc trưng

Cửa sổ dùng các mẫu có 0 ≤ time ≤ 120 giây. Cần ít nhất năm mẫu, mẫu đầu không muộn hơn 20 giây và mẫu cuối không sớm hơn 90 giây. Tín hiệu trong cửa sổ phải hữu hạn, trục thời gian không trùng. Các mẫu xả có dòng nhỏ hơn −0,1 A; cần ít nhất ba mẫu trải dài ít nhất 30 giây. Điện áp và nhiệt độ được kiểm tra theo miền rộng dành cho cell.

Đặc trưng gồm chỉ số chu kỳ; trung bình, cực tiểu, cực đại, độ lệch chuẩn và độ dốc điện áp; trung bình và độ lệch chuẩn dòng; trung bình, cực đại và độ dốc nhiệt độ. Độ dốc được tính bằng fit đường thẳng trên các mẫu xả trong cửa sổ. Không dùng thời gian xả toàn chu kỳ, dung lượng xả hoặc dữ liệu tương lai. Kiểm thử thay tín hiệu sau 120 giây và nhãn mà không làm đổi đặc trưng.

468 chu kỳ của ba pin vượt qua điều kiện kiểm tra, không có chu kỳ bị loại trong thực nghiệm chính. Các kiểm tra này bảo đảm tính nhất quán kỹ thuật, không thay thế xác minh khoa học nguồn dữ liệu.

### 3.3. Cấu hình mô hình

| Mô hình | Cấu hình chính |
| --- | --- |
| Mean baseline | Trung bình SOH huấn luyện |
| Cycle Ridge | StandardScaler; alpha=1; một đặc trưng cycle |
| Signal Ridge | StandardScaler; alpha=10; 11 đặc trưng |
| Random Forest | 200 cây; min_samples_leaf=5; seed=42; n_jobs=2 |
| HistGradientBoosting | 150 vòng; tối đa 15 lá; L2=1; không early stopping; seed=42 |

Các thư viện trực tiếp được ghim phiên bản và toàn bộ môi trường được lưu trong requirements.lock.txt. Metadata ghi phiên bản Python, NumPy, pandas, scikit-learn, thời điểm chạy, seed và tham số. Kết quả có thể khác rất nhỏ do nền tảng số học; cần giữ cùng phiên bản và kiểm tra sai số khi tái lập.

## Chương 4. Kết quả thực nghiệm

### 4.1. So sánh tổng hợp

| model | mae | rmse | r2 |
| --- | --- | --- | --- |
| Mean baseline | 7.729 | 8.898 | -0.126 |
| Cycle Ridge | 4.392 | 4.676 | 0.609 |
| Signal Ridge | 5.300 | 5.508 | 0.492 |
| Random Forest | 1.241 | 1.628 | 0.962 |
| HistGradientBoosting | 1.250 | 1.586 | 0.962 |

Random Forest và HistGradientBoosting đạt sai số thấp hơn hai mô hình Ridge trong thực nghiệm hiện tại. Random Forest giảm MAE khoảng 71,7% so với Cycle Ridge: đây là mức giảm tương đối của MAE, không phải “độ chính xác 98,76%”. HistGradientBoosting có RMSE trung bình hơi thấp hơn Random Forest, trong khi Random Forest có MAE hơi thấp hơn. Với chỉ ba pin, không có cơ sở coi chênh lệch nhỏ giữa hai mô hình cây là ưu thế tổng quát chắc chắn.

![So sánh mô hình](../reports/model_comparison.png)

### 4.2. Kết quả theo pin

| model | held_out_battery | n_train | n_test | mae | rmse | r2 |
| --- | --- | --- | --- | --- | --- | --- |
| Mean baseline | B05 | 300 | 168 | 8.669 | 9.641 | -0.032 |
| Cycle Ridge | B05 | 300 | 168 | 2.053 | 2.330 | 0.940 |
| Signal Ridge | B05 | 300 | 168 | 3.707 | 3.998 | 0.823 |
| Random Forest | B05 | 300 | 168 | 1.255 | 1.610 | 0.971 |
| HistGradientBoosting | B05 | 300 | 168 | 1.047 | 1.373 | 0.979 |
| Mean baseline | B07 | 300 | 168 | 7.349 | 8.931 | -0.239 |
| Cycle Ridge | B07 | 300 | 168 | 5.382 | 5.615 | 0.510 |
| Signal Ridge | B07 | 300 | 168 | 7.985 | 8.071 | -0.012 |
| Random Forest | B07 | 300 | 168 | 1.264 | 1.626 | 0.959 |
| HistGradientBoosting | B07 | 300 | 168 | 1.224 | 1.568 | 0.962 |
| Mean baseline | B18 | 336 | 132 | 7.168 | 8.122 | -0.108 |
| Cycle Ridge | B18 | 336 | 132 | 5.740 | 6.083 | 0.378 |
| Signal Ridge | B18 | 336 | 132 | 4.209 | 4.456 | 0.666 |
| Random Forest | B18 | 336 | 132 | 1.203 | 1.647 | 0.954 |
| HistGradientBoosting | B18 | 336 | 132 | 1.479 | 1.816 | 0.945 |

Random Forest có MAE khoảng 1,20–1,26 điểm phần trăm trên ba pin. Signal Ridge kém Cycle Ridge ở B05 và B07, cho thấy thêm đặc trưng không bảo đảm cải thiện khi quan hệ thực tế không được biểu diễn tốt bằng mô hình tuyến tính. Mean baseline có R² âm ở cả ba pin; trung bình của hai pin huấn luyện không mô tả đủ biến thiên của pin kiểm thử.

![SOH thực tế và dự đoán kiểm thử](../reports/held_out_predictions.png)

### 4.3. Kiểm thử phần mềm và tính tái lập

Bộ kiểm thử xác minh đặc trưng không phụ thuộc tín hiệu sau cửa sổ hoặc nhãn; kiểm tra ranh giới 120 giây, thiếu cột, thiếu mẫu, thời gian trùng, dòng không phải xả, tín hiệu thiếu và nhãn không nhất quán. Kiểm tra kết quả bảo đảm mỗi chu kỳ có đúng một dự đoán kiểm thử cho mỗi mô hình. Kiểm thử ứng dụng chạy luồng dùng CSV mẫu và luồng chưa nhập dữ liệu.

Số lượng và kết quả kiểm thử thực tế được lưu trong `reports/verification.json` bởi script setup. Notebook khám phá được thực thi bằng kernel Python của môi trường hiện tại. Server demo cần khởi động lại sau khi môi trường được khôi phục; việc giữ mô hình trên đĩa không giữ tiến trình server.

### 4.4. Hạn chế

- Chỉ ba pin trong thực nghiệm chính, chưa có khoảng tin cậy đáng tin cậy theo quần thể pin.
- Chưa đối chiếu file MAT gốc; trục thời gian giống nhau giữa các pin là vấn đề cần xác minh.
- Lựa chọn phạm vi dữ liệu hạn chế các trường hợp suy giảm rất sâu hoặc nhãn bằng 0.
- Không biết đầy đủ điều kiện vận hành để kiểm tra chuyển miền nhiệt độ, chế độ dòng và hóa học cell.
- Chưa có dữ liệu bộ pin xe điện, lỗi cảm biến thực tế hoặc so sánh với hệ quản lý pin trên xe.
- Chưa thực hiện ablation đặc trưng, nested tuning, kiểm định thống kê hay dự đoán RUL.
- Cửa sổ 120 giây là lựa chọn kỹ thuật cố định, chưa chứng minh là cửa sổ tối ưu.

## Chương 5. Kết luận và hướng phát triển

Nghiên cứu đã triển khai được quy trình từ tải dữ liệu chuyển đổi, kiểm tra nhãn, trích xuất đặc trưng cửa sổ đầu chu kỳ, đánh giá theo pin đến demo và xuất tài liệu. Kết quả hiện tại hỗ trợ nhận định rằng mô hình cây khai thác tín hiệu đầu chu kỳ tốt hơn hồi quy chỉ dùng số chu kỳ trên ba pin đã xét. Nhận định này giới hạn ở bản chuyển đổi và thiết kế thực nghiệm hiện tại.

Ưu tiên tiếp theo là tải dữ liệu NASA gốc, tái trích xuất từng chu kỳ với trục thời gian đúng và chạy lại toàn bộ pipeline. Sau đó bổ sung nhiều pin và nhóm điều kiện vận hành, đánh giá chuyển miền, thực hiện ablation và lựa chọn tham số bằng tập validation độc lập. Để triển khai cho xe điện cần dữ liệu bộ pin và đánh giá thực địa; không suy diễn từ kết quả cell thử nghiệm.

## Tài liệu và nguồn cần kiểm chứng khi hoàn thiện bản nộp

1. Repository nguồn chuyển đổi: https://github.com/standing-o/SoH_estimation_of_Lithium-ion_battery — README, CSV và LICENSE đã đọc; commit và checksum trong manifest.
2. NASA PCoE Data Set Repository: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/ — nguồn gốc được repository trung gian dẫn; trang hiện bị chặn trong môi trường, chưa xác minh file gốc.
3. CALCE Battery Data: https://calce.umd.edu/battery-data — ứng viên thay thế; chưa sử dụng trong thực nghiệm.
4. Tài liệu API scikit-learn: https://scikit-learn.org/stable/ — các lớp Ridge, RandomForestRegressor, HistGradientBoostingRegressor, LeaveOneGroupOut và Pipeline; phiên bản thực thi trong metadata.

Danh sách trên phân biệt nguồn đã sử dụng với nguồn cần kiểm chứng. Chưa lập tổng quan tài liệu khoa học đầy đủ; cần đọc và trích dẫn các nghiên cứu SOH theo yêu cầu giảng viên trước khi nộp.

## Phụ lục. Tái lập và minh họa

Từ thư mục repository, chạy `bash scripts/setup.sh`. Sau đó chạy `.venv/bin/python -m streamlit run app/streamlit_app.py --server.headless=true --server.address=0.0.0.0 --server.port=8501`.

CSV đầu vào demo gồm time, terminal_voltage, terminal_current và temperature cho đúng một chu kỳ xả. Đơn vị lần lượt là giây, V, A và °C; dòng xả có dấu âm. Demo chỉ dùng cửa sổ đầu, kiểm tra đầu vào và cảnh báo đặc trưng ngoài miền huấn luyện. Mô hình demo được fit trên cả ba pin, nên dự đoán trên mẫu B05 không phải kết quả đánh giá độc lập.

Các tệp kết quả: data_audit.csv, features.csv, excluded_cycles.csv, metrics_summary.csv, metrics_by_battery.csv, predictions.csv và run_metadata.json. Không tự sửa bảng kết quả; nếu thay dữ liệu hoặc cấu hình, phải chạy lại pipeline và tạo lại báo cáo.
