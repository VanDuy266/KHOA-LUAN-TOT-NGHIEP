# SỔ TAY HIỂU CODE, ĐỌC KẾT QUẢ VÀ BẢO VỆ KHÓA LUẬN PINLAB

Sinh viên: Nguyễn Văn Duy — MSSV: 2311553949 — Chuyên ngành: Khoa Học Dữ Liệu.

Tài liệu hướng dẫn học theo dự án hiện tại, không thay thế việc sinh viên chạy lại và kiểm tra. Các bảng lấy trực tiếp từ reports, không điền số thuận lợi bằng tay. Các đoạn lời nói mẫu chỉ là gợi ý diễn đạt; chỉ sử dụng khi đã hiểu nội dung và xác nhận bằng kết quả.

## 1. Đề tài thực sự làm gì?

Tên đăng ký: Phân tích và dự đoán tình trạng sức khỏe pin xe điện bằng các mô hình học máy.

Bài toán thực hiện hiện tại là ước lượng SOH của một cell lithium-ion từ điện áp, dòng, nhiệt độ trong 120 giây đầu chu kỳ xả và số thứ tự chu kỳ. Đây là hồi quy vì đầu ra là một số liên tục, chẳng hạn 89,5%, không phải một nhãn phân loại tốt/xấu.

Dự án không dự đoán mức sạc còn lại SOC, không dự đoán xe đi được bao nhiêu km và chưa đánh giá RUL — tuổi thọ còn lại. Dữ liệu thuộc cell thử nghiệm dẫn nguồn NASA; không phải dữ liệu xe điện Việt Nam và không phải dữ liệu pack đo trên xe đang chạy.

Câu hỏi nghiên cứu: mô hình khai thác tín hiệu đầu chu kỳ có ước lượng SOH trên pin chưa có trong train tốt hơn cách chỉ dựa vào số chu kỳ không? Phải trả lời bằng dữ liệu test giữ riêng pin, không bằng một mẫu demo đã học.

Cách nói trước hội đồng: “Em xây dựng quy trình ước lượng SOH từ tín hiệu đầu chu kỳ xả, so sánh các cấu hình học máy bằng kiểm thử giữ riêng từng pin và triển khai một ứng dụng tra cứu, đánh giá, dự đoán.”

## 2. SOH là gì và nhãn lấy ở đâu?

SOH (%) = 100 × dung lượng xả đo được (Ah) / dung lượng danh định (2 Ah).

Ví dụ minh họa, không phải số liệu của một lần kiểm thử: danh định 2 Ah, đo được 1,8 Ah thì SOH = 90%. Ý nghĩa là dung lượng đo đạt 90% mức danh định, không có nghĩa pin đang còn 90% mức sạc.

Dung lượng tham chiếu capacity có trong dữ liệu chu kỳ xả MATLAB. Sau khi quan sát xả đầy đủ trong thí nghiệm, nó được dùng tạo nhãn để học và kiểm tra. Khi chạy dự đoán, người dùng không phải cung cấp capacity hoặc SOH của chu kỳ đang dự đoán.

Hai cột cần phân biệt: SOH trong bảng đo là tỷ lệ, ví dụ 0,9; soh_pct trong bảng mô hình là phần trăm, ví dụ 90. Không nhân 100 thêm lần nữa. B0006 có dung lượng ban đầu vượt 2 Ah nên SOH hơi trên 100%; quy trình giữ nguyên, không cắt nhãn cho đẹp.

Nếu đưa capacity của chính chu kỳ vào đầu vào thì gần như cho mô hình đáp án, vì nhãn được tính từ capacity. Đó là rò rỉ dữ liệu, không phải mô hình tốt.

## 3. Dataset bao nhiêu và vì sao không học từ hai triệu dòng?

| Thành phần | Số lượng | Ý nghĩa |
| --- | --- | --- |
| Dòng sạc/xả ban đầu | 2.089.050 | Các thời điểm đo thật |
| Dòng sạc thiếu tín hiệu bị loại | 2 | B0018, operation 115 |
| Dòng sạch sạc + xả | 2.089.048 | Bảng toàn bộ phép đo |
| Dòng sạc sạch | 1.903.327 | Không tự có nhãn SOH cho từng dòng |
| Dòng xả | 185.721 | Dùng xây dựng cửa sổ tín hiệu và nhãn |
| Chu kỳ xả / mẫu SOH | 636 | Một chu kỳ tạo một dòng đặc trưng |
| Pin | 4 | B0005, B0006, B0007, B0018 |

Một chu kỳ có nhiều thời điểm đo nhưng có một dung lượng tham chiếu. Vì vậy gom các thời điểm đầu chu kỳ thành một bộ đặc trưng rồi gắn một nhãn SOH. Hai triệu dòng không đồng nghĩa hai triệu mẫu giám sát độc lập; bốn pin vẫn là bốn nhóm pin, và các chu kỳ trong cùng pin vẫn tương quan.

| Pin | Số chu kỳ xả |
| --- | --- |
| B0005 | 168 |
| B0006 | 168 |
| B0007 | 168 |
| B0018 | 132 |

Ba file chính: measurements_all.csv là toàn bộ phép đo; measurements.csv là riêng xả có capacity và SOH; cycle_features.csv là 636 mẫu học máy. Không cộng số dòng của chúng vì hai file sau được tạo từ dữ liệu trong file đầu.

Nguồn thực tế: file MATLAB trong psanabriaUC/BatteryDatasetImplementation, commit ghi ở data/manifest.json. Đã đọc danh mục NASA và README mô tả thí nghiệm, đã kiểm checksum bản lưu; chưa đối chiếu byte với archive S3 của nhà phát hành. Ghi đúng giới hạn này trong báo cáo, không nhận đã xác nhận toàn bộ chuỗi thu thập từ NASA.

## 4. Quy trình làm: từ dữ liệu đến sản phẩm

MATLAB → kiểm checksum → đọc từng operation → làm sạch → tách xả → tạo nhãn và đặc trưng → chia theo pin → học trên train → dự đoán test → tính sai số → fit lại mô hình demo → Vincent D.

### 4.1. Tải và xác minh nguồn

scripts/download_data.py đọc manifest, tải qua HTTPS và so SHA-256. SHA-256 giống dấu vân tay nội dung file: giúp phát hiện tải sai hoặc nội dung thay đổi so với phiên bản đã ghim. Nó không tự chứng minh bản lưu là bản NASA phát hành.

### 4.2. Đọc MATLAB

scripts/prepare_data.py, hàm read_battery, dùng scipy.io.loadmat. Mỗi operation có loại sạc, xả hoặc trở kháng. Vòng lặp chỉ xuất sạc/xả vì trở kháng có cấu trúc khác. Các mảng Time, Voltage_measured, Current_measured, Temperature_measured được chuyển thành DataFrame.

operation_index giữ thứ tự thật trong MATLAB. cycle đếm riêng số lần sạc hoặc xả; không ghép sạc/xả chỉ bằng cycle vì số lần hai loại không bằng nhau.

### 4.3. Làm sạch

Hàm clean_battery loại dòng có tín hiệu thiếu hoặc vô hạn, kiểm thời gian âm, loại dòng trùng hoàn toàn nếu có và từ chối khóa thời gian xung đột. Dữ liệu hiện tại chỉ loại hai dòng sạc B0018 thiếu cả ba tín hiệu, không loại chu kỳ xả nào và không nội suy bù.

scripts/check_dataset.py đọc CSV theo khối 100.000 dòng, kiểm thiếu/vô hạn, trùng khóa và so từng tín hiệu với mảng MATLAB sau xử lý. Kết quả nằm trong reports/dataset_check.json. Đây là kiểm tra tính nhất quán kỹ thuật, không phải xác nhận dùng được trên xe thực tế.

### 4.4. Tạo nhãn và đặc trưng

src/battery_soh/features.py có validate_target để kiểm nhãn và extract_window để tính đầu vào. Hàm không đọc dòng tương lai sau 120 giây để tạo đặc trưng. scripts/prepare_data.py gọi hai hàm cho từng chu kỳ rồi ghi cycle_features.csv.

### 4.5. Học và đánh giá

scripts/run_experiment.py tạo năm cấu hình, giữ riêng lần lượt từng pin, fit trên ba pin còn lại rồi predict pin test. Không tinh chỉnh tham số bằng các kết quả test. CSV lưu từng dự đoán để có thể tính lại chỉ số.

### 4.6. Lưu mô hình để sử dụng

Sau đánh giá, Random Forest được fit lại cả 636 mẫu và lưu artifacts/random_forest.joblib. Đây là mô hình dùng demo, không phải một trong bốn mô hình giữ riêng pin. Kết quả dự đoán từ model fit cả bốn pin trên chính dữ liệu đã học không phải điểm test độc lập.

## 5. Mười một đặc trưng là gì?

| Tên trong code | Ý nghĩa | Số đặc trưng |
| --- | --- | --- |
| cycle | Số thứ tự chu kỳ xả | 1 |
| voltage_mean, voltage_min, voltage_max, voltage_std, voltage_slope | Trung bình, nhỏ nhất, lớn nhất, độ lệch chuẩn và độ dốc điện áp | 5 |
| current_mean, current_std | Trung bình và độ lệch chuẩn dòng | 2 |
| temperature_mean, temperature_max, temperature_slope | Trung bình, lớn nhất và độ dốc nhiệt độ | 3 |

Tổng: 11. Mã pin battery chỉ dùng chia nhóm và theo dõi, không đưa vào X; soh_pct là y; capacity và SOH không thuộc danh sách FEATURES.

Mean cho biết mức trung bình; std cho biết mức biến thiên; slope cho biết xu hướng theo thời gian. Trong code, np.polyfit(time, signal, 1)[0] là hệ số góc của đường thẳng fit tín hiệu. Tương quan hoặc giá trị dự đoán của một đặc trưng không chứng minh quan hệ nhân quả với suy giảm pin.

Cửa sổ cần ít nhất 5 mẫu trong 0–120 giây, mốc đầu không muộn hơn 20 và mốc cuối không sớm hơn 90 giây. Cần ít nhất 3 mẫu có dòng < −0,1 A trải dài ít nhất 30 giây. Thống kê tính trên các mẫu đang xả đó. Cửa sổ 120 giây là lựa chọn kỹ thuật đã cố định; chưa có thực nghiệm chứng minh tối ưu.

## 6. Đọc những dòng code quan trọng

### 6.1. Kiểm tra đúng cửa sổ

```python
window = frame.loc[time <= WINDOW_SECONDS, SIGNALS]
active = window.loc[window.terminal_current < -0.1]
```

Dòng đầu chọn các tín hiệu trong 120 giây đầu. Dòng sau bỏ các điểm chưa thực sự xả theo ngưỡng dòng. Bản thực thi còn chuyển dữ liệu về số và kiểm thiếu, thời gian, số mẫu; không bỏ các kiểm tra đó khi minh họa.

### 6.2. Tách X và y

```python
X = data[FEATURES]
y = data["soh_pct"]
```

X gồm 11 thông tin đầu vào mỗi chu kỳ; y là đáp án tham chiếu cần học. Ví dụ một dòng X gồm cycle=20, các thống kê điện áp/dòng/nhiệt độ; y của dòng đó có thể là SOH 85%. Con số ví dụ này chỉ minh họa định dạng, không phải kết quả một pin đã xác minh.

### 6.3. Tách pin huấn luyện và pin kiểm thử

```python
for train, test in LeaveOneGroupOut().split(data, groups=data.battery):
    model.fit(data.iloc[train][columns], data.iloc[train].soh_pct)
    pred = model.predict(data.iloc[test][columns])
```

train và test là các chỉ số dòng do thư viện tạo theo nhóm pin. fit học từ X_train và y_train. predict chỉ nhận X_test, không nhận nhãn y_test. Sau dự đoán mới so với y_test để tính sai số. Tên model, columns và vòng lặp năm cấu hình được khai báo ở hàm models trong code thực tế.

### 6.4. Chuẩn hóa đúng chỗ

```python
make_pipeline(StandardScaler(), Ridge(alpha=1.0))
```

StandardScaler học trung bình/độ lệch chuẩn từng cột trên train để đưa các đầu vào về thang phù hợp cho Ridge. Pipeline bảo đảm scaler được fit trong từng lần model.fit. Không fit scaler trên toàn bộ dữ liệu trước khi chia rồi dùng thống kê của test.

### 6.5. Tạo Random Forest

```python
RandomForestRegressor(
    n_estimators=200,
    min_samples_leaf=5,
    random_state=42,
    n_jobs=2,
)
```

200 là số cây. min_samples_leaf=5 yêu cầu một lá có ít nhất 5 mẫu huấn luyện, hạn chế các lá quá nhỏ. random_state=42 cố định ngẫu nhiên để tái lập, không làm mô hình tự tốt hơn. n_jobs=2 dùng hai luồng xử lý, không phải hai mô hình hoặc hai lần kiểm thử.

### 6.6. Lưu kết quả và model

```python
mean_absolute_error(y, pred)
root_mean_squared_error(y, pred)
r2_score(y, pred)
```

Ba lời gọi tính MAE, RMSE và R², không phải accuracy phân loại. summary = scores.groupby("model")[["mae", "rmse", "r2"]].mean() lấy trung bình giữa các vòng/pin. joblib.dump lưu model đã fit để giao diện tải lại; giao diện không huấn luyện model mỗi khi có người mở trang.

## 7. Chia train/test thế nào và vì sao?

| Vòng | Pin dùng học | Pin giữ riêng kiểm thử | Số mẫu train | Số mẫu test |
| --- | --- | --- | --- | --- |
| 1 | B0006, B0007, B0018 | B0005 | 468 | 168 |
| 2 | B0005, B0007, B0018 | B0006 | 468 | 168 |
| 3 | B0005, B0006, B0018 | B0007 | 468 | 168 |
| 4 | B0005, B0006, B0007 | B0018 | 504 | 132 |

Không pin nào vừa nằm train vừa nằm test trong cùng vòng. Mỗi chu kỳ nhận đúng một dự đoán kiểm thử cho mỗi cấu hình. Có 4 vòng × 5 cấu hình = 20 lần fit chính; sau đó có một lần fit RF toàn bộ cho demo. Thực nghiệm bổ sung có các lần fit khác, không tính nhầm thành tổng chỉ có 21 lần huấn luyện của cả dự án.

Chia ngẫu nhiên thời điểm có thể đưa các mẫu trong cùng chu kỳ vào cả train/test. Chia ngẫu nhiên chu kỳ vẫn có thể trộn cùng pin. Khi các quan sát tương quan, kết quả có thể lạc quan cho mục tiêu pin mới. Thiết kế theo nhóm phù hợp câu hỏi nghiên cứu hiện tại, không tự chứng minh mọi dạng tổng quát hóa.

Không có tập validation độc lập và chưa có nested tuning. Các tham số đã cố định. Nếu tiếp tục đổi tham số/đặc trưng theo điểm test hiện tại rồi chọn kết quả tốt nhất, phải có thiết kế validation độc lập để đánh giá lựa chọn đó.

## 8. Năm cấu hình mô hình: tốt và chưa tốt ở đâu?

Đây là năm cấu hình so sánh, không phải năm thuật toán hoàn toàn khác nhau: một baseline trung bình, hai cấu hình Ridge và hai họ mô hình cây.

### 8.1. Mean baseline — Trung bình SOH

DummyRegressor(strategy="mean") học trung bình nhãn train và dự đoán một giá trị cố định. Mặc dù code truyền cột cycle theo yêu cầu giao diện fit, baseline trung bình không dùng cycle để tạo quan hệ thay đổi đầu ra.

Điểm mạnh là dễ hiểu và tạo mốc tối thiểu. Nếu một mô hình phức tạp không hơn baseline này thì cần xem lại giá trị thực tiễn. Điểm yếu là không theo được suy giảm và khác biệt tín hiệu; R² trung bình hiện âm. Không coi baseline thấp là bằng chứng mô hình còn lại đã sẵn sàng thực địa.

### 8.2. Cycle Ridge — Ridge theo chu kỳ

Đầu vào chỉ có số chu kỳ. Mô hình tuyến tính có phạt L2, alpha=1, sau chuẩn hóa. Điểm mạnh là đơn giản, dễ trình bày xu hướng và làm baseline hợp lý hơn dự đoán trung bình. Ở B0005 nó có MAE thấp hơn RF.

Điểm yếu là chỉ số chu kỳ không chứa đủ thông tin về nhiệt độ/tải/sự khác nhau giữa pin. Hành vi suy giảm phi tuyến hoặc chuyển điều kiện có thể không được biểu diễn tốt. Không kết luận nó luôn kém RF chỉ vì điểm macro cao hơn.

### 8.3. Signal Ridge — Ridge theo tín hiệu

Dùng cả 11 đặc trưng, alpha=10, chuẩn hóa trong Pipeline. Điểm mạnh là kiểm tra một quan hệ tuyến tính có nhiều tín hiệu và có thể diễn giải hệ số nếu phân tích đúng thang đo. Dự án chưa có phân tích hệ số để kết luận nguyên nhân vật lý.

Trong kết quả hiện tại, cấu hình này kém Cycle Ridge ở macro MAE và lỗi nặng trên B0007. Thêm đặc trưng không bảo đảm cải thiện; quan hệ giữa pin có thể không phù hợp dạng tuyến tính của cấu hình. Cycle Ridge và Signal Ridge cũng khác alpha, nên so sánh hai cấu hình không cô lập hoàn toàn tác động “thêm đặc trưng”.

### 8.4. Random Forest — Rừng ngẫu nhiên

Kết hợp nhiều cây hồi quy; các cây học từ các mẫu bootstrap và dự đoán hồi quy được tổng hợp bằng trung bình. Dự án dùng thư viện scikit-learn. Lưu ý default max_features=1.0 của RandomForestRegressor phiên bản đang dùng cho phép xét toàn bộ đặc trưng ở mỗi lần chia; không nói code đã chủ động chọn sqrt(số đặc trưng) như thường gặp trong ví dụ phân loại.

Điểm mạnh: biểu diễn quan hệ phi tuyến và tương tác mà không cần chỉ định một đường thẳng; không cần StandardScaler trong cấu hình hiện tại; có macro MAE thấp nhất trong năm cấu hình giữ riêng pin. Điểm yếu: nhiều cây khó giải thích như một phương trình; chỉ bốn pin nên chưa chắc tổng quát rộng; mô hình cây không mạnh về ngoại suy xu hướng ra ngoài vùng đã học. Trong kiểm thử theo thời gian nó còn kém baseline cuối đã biết.

RF được quy định trước cho demo, không phải qua một vòng chọn tham số tối ưu trên test. Điểm số hiện tại hỗ trợ lựa chọn thực hành này nhưng không chứng minh tối ưu toàn cục.

### 8.5. HistGradientBoosting — Tăng cường cây theo histogram

Các cây được xây dựng tuần tự để giảm hàm mất mát, kết hợp thành dự đoán. Phân biệt với RF: RF xây nhiều cây trên các mẫu bootstrap rồi tổng hợp; boosting bổ sung cây theo quá trình cải thiện mô hình cộng dồn. Với hàm mất mát bình phương, có thể hiểu trực giác là các cây sau học tín hiệu liên quan sai số còn lại.

Điểm mạnh là biểu diễn quan hệ phi tuyến, thường hữu ích với dữ liệu bảng, và kết quả hiện tốt hơn hai cấu hình Ridge xét macro MAE. Điểm yếu: cấu hình hiện kém RF; phụ thuộc siêu tham số và cần validation nếu muốn tối ưu. Không kết luận thuật toán boosting luôn kém RF dựa trên một cấu hình và bốn pin.

## 9. So sánh bằng gì và đọc số ra sao?

| model | mae | rmse | r2 |
| --- | --- | --- | --- |
| Mean baseline | 8.594 | 9.811 | -0.090 |
| Cycle Ridge | 4.074 | 4.474 | 0.690 |
| Signal Ridge | 7.405 | 7.712 | -0.262 |
| Random Forest | 2.724 | 3.189 | 0.878 |
| HistGradientBoosting | 3.286 | 3.608 | 0.843 |

MAE và RMSE càng thấp càng tốt. R² càng cao càng tốt trong cùng cách đánh giá, nhưng R²=0,878 không đồng nghĩa accuracy=87,8%. Đây không phải bài toán phân loại nên không dùng accuracy, precision, recall hoặc F1 nếu chưa xây dựng một bài toán phân loại riêng.

### 9.1. Ví dụ tự tính sai số

Ví dụ minh họa: SOH thật [90, 80, 70], dự đoán [88, 83, 69]. Sai số dự đoán − thật là [-2, 3, -1]. MAE = (2+3+1)/3 = 2 điểm phần trăm. RMSE = sqrt((4+9+1)/3), khoảng 2,160. R² của ví dụ là 0,93. Đây là bộ ba số minh họa, không phải kết quả của dataset.

MAE RF hiện 2,724 nghĩa là lấy sai số tuyệt đối trong mỗi pin test rồi lấy trung bình giữa bốn pin, được khoảng 2,724 điểm phần trăm SOH. Không có nghĩa mọi mẫu đều sai đúng 2,724, không phải biên sai số bảo đảm và không được gọi là “độ chính xác 97,276%”.

RMSE cao hơn MAE phản ánh ảnh hưởng của những sai số lớn hơn; chỉ nhìn hai số này chưa đủ biết chu kỳ nào sai nhiều, cần đọc dự đoán và đồ thị lỗi. R² âm nghĩa mô hình có SSE lớn hơn SST khi so với trung bình nhãn của pin test; không nói nó là “accuracy âm”.

### 9.2. Tại sao lấy trung bình theo pin?

Mỗi pin có một MAE/RMSE/R². Sau đó trung bình bốn giá trị, không trọng số. B0018 có 132 chu kỳ nhưng được trọng số một phần tư, giống các pin 168 chu kỳ. Chỉ số gộp tất cả 636 mẫu có thể khác; trung bình R² cũng không phải R² tính trên dữ liệu gộp.

### 9.3. RF có thắng ở mọi pin không?

| held_out_battery | model | mae | rmse |
| --- | --- | --- | --- |
| B0005 | Cycle Ridge | 1.253 | 1.537 |
| B0005 | Random Forest | 1.603 | 2.151 |
| B0006 | Cycle Ridge | 4.533 | 4.899 |
| B0006 | Random Forest | 3.979 | 4.627 |
| B0007 | Cycle Ridge | 5.342 | 5.948 |
| B0007 | Random Forest | 2.086 | 2.484 |
| B0018 | Cycle Ridge | 5.171 | 5.511 |
| B0018 | Random Forest | 3.228 | 3.495 |

Không. B0005 có Cycle Ridge MAE khoảng 1,253, thấp hơn RF khoảng 1,603. B0006 là trường hợp RF có MAE cao nhất trong bốn pin. Kết luận đúng là RF có macro MAE thấp nhất trong năm cấu hình hiện tại, không phải tốt nhất mọi trường hợp.

Signal Ridge ở B0007 có MAE khoảng 16,229 và R² khoảng -3,124. Phải giữ kết quả bất lợi này trong báo cáo, không loại pin để tăng chỉ số sau khi thấy điểm.

## 10. Hai phân tích bổ sung và kết quả không thuận lợi

### 10.1. Bỏ nhóm đặc trưng

| configuration | mae | rmse |
| --- | --- | --- |
| Full features | 2.724 | 3.189 |
| Without cycle | 2.768 | 3.349 |
| Without temperature | 2.590 | 3.048 |

Bỏ số chu kỳ làm MAE thay đổi nhẹ. Bỏ nhiệt độ có MAE thấp hơn cấu hình đầy đủ ở dữ liệu hiện tại. Có thể nói nhóm nhiệt độ chưa cho lợi ích trong thiết kế này; không nói nhiệt độ không ảnh hưởng pin hoặc không có giá trị ở mọi điều kiện.

Đây là phân tích sau thực nghiệm chính. Không âm thầm chọn cấu hình bỏ nhiệt độ vì biết điểm test rồi nhận điểm đó như đánh giá độc lập cho một quy trình đã tối ưu.

### 10.2. Chia theo thời gian 70/30

| battery | model | n_train | n_test | mae |
| --- | --- | --- | --- | --- |
| B0005 | Random Forest | 117 | 51 | 4.453 |
| B0005 | Last known SOH | 117 | 51 | 3.308 |
| B0006 | Random Forest | 117 | 51 | 5.474 |
| B0006 | Last known SOH | 117 | 51 | 4.542 |
| B0007 | Random Forest | 117 | 51 | 3.667 |
| B0007 | Last known SOH | 117 | 51 | 2.766 |
| B0018 | Random Forest | 92 | 40 | 2.570 |
| B0018 | Last known SOH | 92 | 40 | 2.102 |

RF kém cách giữ SOH cuối đã biết ở cả bốn pin trong thiết kế này. Có thể lý giải về mặt mô hình rằng cây không tự ngoại suy xu hướng suy giảm vượt vùng quan sát; chưa có thí nghiệm tách riêng mọi nguyên nhân để kết luận nhân quả.

Hai thiết kế hỏi hai câu khác nhau: LOBO hỏi pin mới; 70/30 hỏi chu kỳ tương lai trên pin đã thấy. Không gộp chúng thành một bảng “accuracy chung” hoặc chọn kết quả tốt để bỏ kết quả xấu. Không nhận sản phẩm đã dự đoán tuổi thọ còn lại.

## 11. Notebook là gì và dùng thế nào?

notebooks/01_eda.ipynb gồm ô văn bản, ô code và kết quả như bảng/biểu đồ. EDA là phân tích khám phá dữ liệu. Notebook hiện đọc các bảng đã chuẩn bị, thống kê theo pin, vẽ SOH và tương quan, đọc kết quả thực nghiệm. Quy trình huấn luyện chính nằm trong scripts/run_experiment.py, không nằm ở một mô hình bí mật trong notebook.

Mở cả thư mục gốc trong VS Code, cài tiện ích Jupyter, chọn kernel Python của .venv rồi Run All khi đã có reports. Không tự chọn Python toàn cục 3.14 nếu dự án đang dùng 3.12. Notebook cần chạy với thư mục làm việc gốc có reports; nếu báo không thấy features.csv, kiểm tra working directory trước khi đổi đường dẫn tùy tiện.

Tương quan chỉ mô tả quan hệ trong dữ liệu quan sát, không chứng minh nguyên nhân và không đủ chọn đặc trưng dựa trên toàn bộ test. Colab có thể dùng đọc notebook nếu đã upload đúng cấu trúc dữ liệu, nhưng sản phẩm Vincent D nên demo bằng VS Code và trình duyệt trên máy chuẩn bị sẵn.

## 12. Từng file code làm gì?

| File | Đầu vào / tác dụng | Đầu ra cần tìm |
| --- | --- | --- |
| scripts/download_data.py | Manifest, tải và xác minh MAT | data/mat |
| scripts/prepare_data.py | Đọc MAT, làm sạch, tạo đặc trưng | data/clean, nhật ký, thống kê |
| scripts/check_dataset.py | So CSV sạch với từng mảng MAT | reports/dataset_check.json |
| src/battery_soh/features.py | Nhãn và 11 đặc trưng đầu chu kỳ | Hàm dùng chung train/demo |
| scripts/run_experiment.py | Năm cấu hình, kiểm thử theo pin | metrics, predictions, model joblib |
| scripts/analyze_results.py | Bỏ nhóm đặc trưng, chia thời gian | ablation, temporal_metrics, hình lỗi |
| app/streamlit_app.py | Điểm vào, kiểm file, chọn màn hình | Ứng dụng Vincent D |
| app/app_data.py | Đọc file có cache theo thời điểm sửa | Bảng và model cho giao diện |
| app/prediction.py | Đọc CSV, kiểm một pin/chu kỳ, dự đoán | SOH, đặc trưng, cảnh báo ngoài miền |
| app/labels.py | Dịch tên hiển thị trên bản sao | Bảng tiếng Việt |
| app/charts.py | Biểu đồ Altair | Đồ thị tương tác |
| app/components.py | Tiêu đề, thẻ số liệu, nút CSV | Thành phần hiển thị dùng chung |
| app/styles.css | Màu, bố cục, chuyển động | Không tham gia tính toán SOH |
| app/screens | Năm hàm render cho năm màn hình | Tổng quan, tra cứu, đánh giá, dự đoán, hồ sơ |
| tests | Kiểm rò rỉ, dữ liệu, dự đoán và giao diện | pytest-results.xml, verification.json |

pandas giúp chọn cột/nhóm chu kỳ, NumPy tính thống kê, scipy đọc .mat, scikit-learn học và đánh giá, joblib lưu mô hình, matplotlib tạo hình báo cáo, Altair vẽ tương tác, Streamlit dựng giao diện. Không có API LLM dùng để suy ra SOH. Các thuật toán thư viện cần được ghi nhận; việc biết gọi fit không thay cho hiểu thiết kế dữ liệu.

## 13. Chạy Vincent D đúng cách trên máy Windows

Lỗi gần nhất “không tìm thấy .venv\Scripts\python.exe” nghĩa là môi trường chưa tạo thành công hoặc không nằm ở vị trí đang gọi. ZIP không kèm môi trường Python của máy khác. Không giải quyết bằng việc liên tục chạy lại cùng một đường dẫn chưa tồn tại.

Đứng tại thư mục có README.md và requirements-app.txt, không đứng trong app. Kiểm tra:

```powershell
py -3.12 --version
Test-Path .\requirements-app.txt
Test-Path .\.venv\Scripts\python.exe
```

Nếu chưa có Python 3.12, cài bằng Python Install Manager với py install 3.12 nếu được hỗ trợ, hoặc cài Python 3.12 từ python.org. Khi lệnh kiểm tra phiên bản thành công, chạy:

```powershell
powershell -ExecutionPolicy Bypass -File .\chay_windows.ps1
```

Script tạo .venv nếu thiếu, cài thư viện và kiểm mã thoát từng bước; có dữ liệu/mô hình demo thì dùng lại, nếu không thì chuẩn bị. Không bấm Ctrl+C giữa lúc pip đang cài. Nếu bước trước lỗi, dừng và đọc lỗi đó trước khi chạy tiếp.

Sau khi môi trường sẵn sàng, lệnh mở sản phẩm là:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app\streamlit_app.py
```

Mở localhost:8501 trên chính máy đang chạy. Không bấm Run Python File/F5 vào streamlit_app.py như script Python thông thường. Cách đó không tạo runtime Streamlit và có thể chạy nhầm Python toàn cục. Chỉ sao chép lệnh, không sao chép dấu nhắc PS hoặc >>. Không đóng terminal trong lúc demo.

### 13.1. Chạy lại nghiên cứu để kiểm chứng

Sau khi tạo .venv và cài thư viện ứng dụng:

```powershell
.\.venv\Scripts\python.exe scripts\download_data.py
.\.venv\Scripts\python.exe scripts\prepare_data.py
.\.venv\Scripts\python.exe scripts\check_dataset.py
.\.venv\Scripts\python.exe scripts\run_experiment.py
.\.venv\Scripts\python.exe scripts\analyze_results.py
```

Muốn chạy pytest, notebook và xuất Word/PowerPoint phải cài requirements.txt, không chỉ requirements-app.txt:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\build_notebook.py
.\.venv\Scripts\python.exe scripts\build_documents.py
.\.venv\Scripts\python.exe scripts\build_study_guide.py
```

Các bước Python/pipeline đã kiểm chứng ở môi trường Linux. Script PowerShell được xem xét nhưng chưa chạy trực tiếp trên máy Windows của sinh viên. Không nói máy cá nhân đã chạy thành công trước khi có kết quả tại đó.

## 14. Trình bày trước hội đồng theo thứ tự nào?

### 14.1. Phần slide

Mở docs/slide-bao-ve.pptx. Thời lượng đề xuất khoảng 10–15 phút cần điều chỉnh theo khoa, không phải quy định chính thức.

| Thời gian gợi ý | Nội dung | Điều cần nói được |
| --- | --- | --- |
| 1 phút | Đề tài và mục tiêu | Ước lượng SOH, không phải SOC/RUL |
| 2 phút | Nguồn và chất lượng dữ liệu | 2 triệu dòng, 4 pin, 636 mẫu, 2 dòng bị loại |
| 2 phút | Phương pháp | 11 đặc trưng đầu 120 giây, không dùng nhãn làm đầu vào |
| 2 phút | Cách đánh giá | Bốn vòng giữ riêng pin, năm cấu hình, tham số cố định |
| 2 phút | Kết quả | MAE/RMSE/R², RF tốt ở macro nhưng không mọi trường hợp |
| 2–3 phút | Demo Vincent D | Tra cứu, đánh giá, upload CSV, tải kết quả |
| 1 phút | Hạn chế và hướng phát triển | Chỉ bốn pin, chưa thực địa, cần thêm dữ liệu |

### 14.2. Lời nói mẫu khi đọc bảng kết quả

“Em so sánh năm cấu hình trên cùng bốn vòng giữ riêng pin. Random Forest có MAE trung bình khoảng 2,724 điểm phần trăm SOH, thấp hơn Cycle Ridge khoảng 4,074 trong thiết kế hiện tại. Tuy nhiên, RF không thắng trên mọi pin; riêng B0005, Cycle Ridge tốt hơn. Kết quả chưa đại diện pin xe điện thực tế.”

“Trong kiểm thử theo thời gian, RF lại kém baseline giữ SOH cuối đã biết. Vì vậy em giới hạn kết luận ở ước lượng SOH theo thiết kế đã đánh giá, chưa nhận sản phẩm dự đoán được RUL.”

### 14.3. Demo trên trình duyệt

Mở app trước, giữ terminal, rồi trình chiếu slide. Đến phần demo dùng Alt+Tab sang trình duyệt. Tổng quan: chỉ số và hồ sơ sinh viên. Tra cứu pin: chọn B0005 và một chu kỳ, xem tín hiệu. Đánh giá: chọn RF, đối chiếu test trên B0005, chỉ ra Ridge có trường hợp tốt hơn. Dự đoán: dùng mẫu hoặc upload examples/chu_ky_mau_B0005.csv, bấm Ước lượng SOH, tải kết quả. Hồ sơ: chỉ mở nguồn/tài liệu khi cần.

Mẫu B0005 đã nằm trong huấn luyện model demo. Nếu hiện khoảng 91,47% thì đó là ví dụ thao tác theo artifact đã bàn giao, không phải chứng minh độ chính xác trên pin lạ. Phiên bản thư viện/model khác có thể cho số khác; bảng kiểm thử mới là cơ sở đánh giá.

### 14.4. Khi hội đồng hỏi code

Không mở toàn bộ hàng trăm dòng từ đầu. Mở đúng câu hỏi: features.py cho đặc trưng/nhãn, models() cho thuật toán/tham số, vòng LeaveOneGroupOut cho chia tập, analyze_results.py cho phân tích bổ sung và app/prediction.py cho upload/dự đoán. Giải thích mục đích mỗi đoạn, đầu vào và đầu ra trước khi nói cú pháp.

## 15. Câu hỏi thường gặp và cách trả lời có căn cứ

**Vì sao dùng học máy?** Để kiểm tra khả năng ước lượng SOH từ tín hiệu quan sát thay vì chỉ số chu kỳ. Cần so với baseline để biết có lợi ích trong dữ liệu hiện tại hay không.

**Có phải năm thuật toán khác nhau?** Không. Năm cấu hình gồm baseline, hai Ridge, RF và boosting. Cách nói phải phản ánh đúng mã.

**Tại sao dùng RF?** Đã quy định cho demo; có khả năng phi tuyến và macro MAE thấp nhất ở cấu hình hiện tại. Chưa chứng minh tối ưu toàn cục hoặc hơn ở mọi pin.

**Có cần nhiều mô hình hơn không?** Không tăng số lượng chỉ để đủ tên. Nên bổ sung khi nó trả lời giả thuyết rõ và có validation phù hợp. Với dữ liệu nhãn nhỏ, mạng sâu không tự bảo đảm tốt hơn.

**Sao không dùng toàn bộ hai triệu dòng làm X?** Mỗi nhãn thuộc chu kỳ xả; dùng từng thời điểm như mẫu độc lập dễ sai đơn vị quan sát và rò rỉ. Bài toán hiện đã định nghĩa một chu kỳ là một mẫu.

**Sao không dùng phần sạc để tăng nhãn?** Phần sạc không tự có nhãn capacity cùng thời điểm. Muốn dùng cần định nghĩa cách liên kết hoạt động và thời điểm dự đoán, tránh dùng thông tin tương lai; không tự nhân bản nhãn để tăng số lượng.

**SOH 90% có nghĩa còn đi 90% quãng đường không?** Không suy trực tiếp. Quãng đường còn phụ thuộc SOC, pack, tải, môi trường và hệ thống xe; dự án chưa có dữ liệu đó.

**35 test đạt có nghĩa mô hình đúng 100% không?** Không. Đó là kiểm tra các điều kiện phần mềm/dữ liệu đã viết. Độ tốt của ước lượng phải dựa trên thực nghiệm và còn giới hạn dữ liệu.

**Phần nào sinh viên thực hiện?** Giải thích trung thực việc tổ chức và kiểm chứng nguồn, làm sạch, định nghĩa mẫu/nhãn/đặc trưng, thiết kế train/test, so sánh, phân tích lỗi và ứng dụng. Thuật toán thư viện không phải do sinh viên phát minh; ghi nhận hỗ trợ theo quy định trường.

**Giới hạn chính là gì?** Bốn cell phòng thí nghiệm, bản lưu MATLAB chưa đối chiếu byte với S3, chưa có dữ liệu Việt Nam/pack/xe thực tế, chưa nested tuning, mô hình kém baseline ở thiết kế thời gian.

## 16. Tự luyện để thật sự hiểu

Bài 1: lấy một dòng features, chỉ ra X là 11 cột nào, y là cột nào, battery dùng làm gì. Không chỉ đọc thuộc tên.

Bài 2: lấy một chu kỳ, mở 120 giây đầu và tự tính mean điện áp trên mẫu đang xả; đối chiếu features.py. Không dùng toàn chu kỳ để tính lại rồi cho rằng code sai.

Bài 3: lọc reports/predictions.csv theo RF và B0005, tự tính trung bình trị tuyệt đối predicted_soh − actual_soh; phải xấp xỉ 1,603, không phải macro 2,724.

Bài 4: tìm trường hợp model kém và giải thích được ít nhất một điều đã chứng minh, một giả thuyết chưa chứng minh. Không tự gán nguyên nhân vật lý từ biểu đồ.

Bài 5: tắt ứng dụng, mở lại đúng .venv; chạy mẫu, chạy CSV thiếu cột để thấy lỗi; thay đầu vào để xác nhận kết quả cũ biến mất. Tập nói trong lúc thao tác, không chỉ chiếu giao diện.

Bài 6: thực hành một lượt bảo vệ có slide, demo và trả lời câu hỏi giới hạn. Khi chưa biết một yêu cầu của khoa hoặc một nguyên nhân thực nghiệm, nói rõ chưa xác minh thay vì đoán.

## 17. Checklist bàn giao

Báo cáo Word/PDF đúng mẫu được giảng viên xác nhận; slide; mã nguồn và README; dataset hoặc nguồn/hướng dẫn tái tạo; model joblib; bảng/chỉ số/dự đoán test; notebook; video demo dự phòng nếu cần. ZIP, GitHub và giao diện không thay thế xác nhận học thuật hoặc quy cách nộp chính thức.

Các file kết quả quan trọng để đối chiếu: reports/metrics_summary.csv, metrics_by_battery.csv, predictions.csv, ablation_summary.csv, temporal_metrics.csv, dataset_summary.json, dataset_check.json và verification.json.
