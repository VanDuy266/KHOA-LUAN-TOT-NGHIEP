# Cấu trúc mã nguồn và phương pháp xử lý

Tôi chia chương trình thành bốn phần: dữ liệu, mô hình, đánh giá và giao diện. Mỗi phần có đầu vào và đầu ra riêng để kiểm tra được kết quả.

## 1. Dữ liệu và khóa chu kỳ

Nguồn SDU công bố năm 2025 có 86 pin qua hai giai đoạn. Bản chọn dùng trong sản phẩm có 10.505.065 dòng đo và 20.823 mẫu chu kỳ. Một mẫu được xác định bởi `battery + phase + cycle`; số chu kỳ có thể lặp khi đổi giai đoạn nên không bỏ cột `phase` khỏi khóa.

`download_data.py` nhận gói ZIP tải về hoặc lấy nhánh dữ liệu riêng bằng Git. `prepare_data.py` kiểm SHA-256 của nội dung nguồn, đọc từng file, sắp bản sao theo chu kỳ/thời gian rồi tạo Parquet. CSV nguồn không bị ghi đè. Mỗi file Parquet ứng với một pin trong một giai đoạn; mỗi nhóm dòng Parquet ứng với một chu kỳ để đọc nhanh.

Bảng `cycle_features.csv` chứa cả thông tin kiểm tra và nhãn. Chỉ các tên trong hằng `FEATURES` được dùng làm đầu vào mô hình. Không đưa mọi cột của bảng vào `fit()`.

## 2. Hàm tính đặc trưng

`src/battery_soh/features.py` có hai hàm chính:

| Hàm | Mục đích |
| --- | --- |
| `extract_window(frame, cycle)` | Kiểm tín hiệu, lấy 0–120 giây, chọn phần đang xả và tính 12 đặc trưng |
| `validate_target(frame)` | Kiểm dung lượng/SOH hữu hạn, nhất quán và đúng mẫu số 2,4 Ah |

`voltage_mean` là điện áp trung bình, `voltage_std` là độ lệch chuẩn. `voltage_slope` tính bằng tổng tích thời gian đã trừ trung bình với điện áp đã trừ trung bình, chia cho tổng bình phương thời gian đã trừ trung bình. Nhiệt độ cũng có độ dốc tương tự.

`phase_code` bằng 0 cho sử dụng ban đầu và 1 cho tái sử dụng. `cycle` và `phase_code` là thông tin giả định có sẵn khi dự đoán. Dung lượng xả toàn chu kỳ chỉ tạo nhãn `soh_pct = capacity_ah / 2.4 * 100`.

## 3. Huấn luyện mô hình bảng

`scripts/run_experiment.py` định nghĩa mốc trung bình, Ridge, Random Forest và LightGBM. Mỗi cấu hình được fit lại trong từng vòng GroupKFold. Bộ chuẩn hóa của Ridge nằm trong Pipeline nên chỉ học từ phần train.

Ví dụ luồng chính:

```python
for train, test in splits:
    model.fit(data.iloc[train][columns], data.iloc[train].soh_pct)
    predicted = model.predict(data.iloc[test][columns])
```

`train` và `test` là vị trí mẫu; `columns` là đúng danh sách đầu vào. Nhóm chia tập là mã pin vật lý, không phải từng dòng cảm biến. Hai giai đoạn của pin kiểm thử không xuất hiện trong train.

`save_models.py` học lại các mô hình bảng trên toàn bộ dữ liệu để bàn giao. Bản học lại không tạo chỉ số kiểm thử. Random Forest được ứng dụng sử dụng tại `artifacts/random_forest.joblib`.

## 4. GRU

`train_gru.py` đọc cửa sổ đầu xả, tạo chuỗi 25 vị trí của V/I/T. Nội suy chỉ tạo biểu diễn dẫn xuất trong bộ nhớ; không sửa dữ liệu gốc. Mỗi mẫu gồm chuỗi `[25, 3]` và hai biến ngữ cảnh `[phase_code, cycle]`.

Lớp `HealthGRU` có GRU 24 đơn vị ẩn. Trạng thái cuối được ghép ngữ cảnh rồi đưa qua lớp Linear/ReLU/Linear. Vòng học tối ưu MSE bằng Adam, 20 epoch và batch 256. Tất cả thang chuẩn hóa lấy từ train trong từng vòng. Trọng số học lại toàn bộ nằm ở `artifacts/gru.pt`, tham số chuẩn hóa ở `artifacts/gru.json`.

## 5. Đánh giá

`reports/predictions.csv` chứa dự đoán ngoài tập học của từng mẫu và tên mô hình, vòng, pin, giai đoạn, chu kỳ. `metrics_by_battery.csv` tính MAE/RMSE/R² theo từng pin. `metrics_summary.csv` lấy trung bình 86 pin; không phải R² tính gộp tất cả mẫu.

| Chỉ số | Ý nghĩa |
| --- | --- |
| MAE | Độ lớn sai số trung bình; thấp hơn tốt hơn |
| RMSE | Sai số nhạy với trường hợp lệch lớn; thấp hơn tốt hơn |
| R² | Mức cải thiện so với dự đoán trung bình trong nhóm đánh giá; có thể âm |

MAE 1,619 nghĩa là sai số trung bình 1,619 điểm phần trăm SOH trong thiết kế đã chạy. Không diễn giải thành độ chính xác 98,381%.

`analyze_results.py` làm hai thí nghiệm riêng. Bỏ đặc trưng kiểm tính hữu ích của số chu kỳ, giai đoạn và nhóm điện áp. Kiểm thử thời gian học 70% chu kỳ đầu của từng pin/giai đoạn, kiểm tra 30% cuối, so với SOH cuối đã biết. Bài toán này khác kiểm thử pin mới.

## 6. Ứng dụng

| File | Vai trò |
| --- | --- |
| `streamlit_app.py` | Tạo trang, thanh điều hướng và kiểm file cần thiết |
| `app_data.py` | Bộ nhớ đệm, nạp mô hình và đọc đúng chu kỳ Parquet |
| `screens/overview.py` | Tổng quan dữ liệu và SOH theo giai đoạn |
| `screens/explorer.py` | Lọc, xem tín hiệu, so sánh hai chu kỳ và xuất CSV |
| `screens/evaluation.py` | Đọc kết quả kiểm thử, không tự huấn luyện |
| `screens/forecast.py` | Nhận CSV, dự đoán một chu kỳ hoặc theo lô |
| `screens/history.py` | Lịch sử trong phiên, xuất và xóa lịch sử |
| `screens/quality.py` | Nguồn, tiến trình chọn và điểm nghi vấn |
| `screens/profile.py` | Thông tin tác giả, phạm vi và tài liệu |
| `prediction.py` | Chuẩn hóa tên cột, kiểm CSV, tách nhóm và gọi mô hình |
| `result_report.py` | Tạo phiếu HTML, thoát ký tự đầu vào và quản lý lịch sử |
| `labels.py` | Tên tiếng Việt trên bản sao hiển thị |

## 7. Kiểm tra và tái lập

`check_dataset.py` đọc toàn bộ 10.505.065 dòng theo từng lô để kiểm số dòng, tín hiệu, nhãn và khóa. Các bài pytest kiểm rò rỉ đặc trưng tương lai, phân hoạch pin, đối chiếu chỉ số từ dự đoán đã lưu, CSV và các màn hình.

`reproduce.py` điều phối lần lượt các bước và dừng khi có lỗi. `build_notebook.py` thực thi notebook trước khi lưu. `build_documents.py` lấy số liệu thực từ CSV để tạo báo cáo và slide, không ghi cứng kết quả trong nội dung báo cáo.

## 8. Giám sát xu hướng SOH

`src/battery_soh/anomaly.py` tạo đặc trưng theo từng pin và giai đoạn, dùng các khoảng quan sát trước đó. `rate_per100` là biến thiên SOH trên 100 số chu kỳ; `innovation_pp` là chênh lệch so với dự kiến từ tốc độ trung vị quá khứ. Nền và MAD không dùng các điểm tương lai.

`scripts/analyze_anomalies.py` chạy Isolation Forest với cùng 5 nhóm pin. Ngưỡng của mỗi vòng lấy từ phân vị 99% điểm train. Quy tắc bổ sung yêu cầu độ lệch chuẩn hóa >4,5 và độ lệch tuyệt đối ≥1 điểm phần trăm SOH. Tổ hợp là cờ theo một trong hai phương pháp. Không tự xóa hoặc sửa dữ liệu được gắn cờ.

Đây là giám sát chuỗi SOH tham chiếu đã quan sát, không phải dự đoán từ BMS trực tuyến. `reports/anomaly_predictions.csv` ghi từng chu kỳ và lý do; `anomaly_summary.csv` ghi số cờ; `anomaly_metadata.json` ghi phương pháp và giới hạn; `artifacts/anomaly_iforest.joblib` là mô hình học lại toàn bộ để bàn giao. Không có nhãn lỗi thực nên không gọi tỷ lệ gắn cờ là độ chính xác.

## 9. Ridge–RF hiệu chỉnh phần dư

`src/battery_soh/hybrid.py` có lớp `RidgeResidualForest`. `fit()` chuẩn hóa và học Ridge trên train, tạo phần dư train rồi học RF từ cùng đặc trưng. `predict()` cộng hai dự đoán. Không đưa y hoặc phần dư làm cột đầu vào khi suy luận. `scripts/evaluate_hybrid.py` dùng đúng phân hoạch pin cũ, lưu dự đoán giữ riêng, so sánh cặp theo pin và mô hình học lại toàn bộ. Đây là phương án kết hợp để kiểm chứng, không phải tuyên bố thuật toán mới.

## Phần thực nghiệm XJTU

| File | Công việc |
| --- | --- |
| scripts/download_xjtu.py | Tải đúng 23 MAT Batch-1/2 từ ZIP tác giả, kiểm CRC và ghi SHA-256; không sửa nguồn |
| src/battery_soh/xjtu.py | Đọc MAT theo chu kỳ; dùng system_time, tách 120 giây đầu xả, kiểm dung lượng; tính SOH theo 2 Ah |
| scripts/prepare_xjtu.py | Xử lý lần lượt từng pin; lưu đặc trưng, chuỗi GRU và nhật ký kiểm tra riêng |
| scripts/evaluate_xjtu.py | Chia 5 nhóm pin; chạy bốn mô hình, mốc trung bình và hai phương án kết hợp; kiểm tra chuyển nguồn/batch |
| scripts/analyze_xjtu.py | Tìm đặc trưng ngoài khoảng SDU, phân tích sai số theo batch và so sánh cặp theo pin |
| scripts/check_xjtu.py | Đối chiếu nhãn, khóa, nhóm pin và tính lại MAE/RMSE từ dự đoán lưu |
| scripts/save_xjtu_models.py | Refit hai RF cho ứng dụng; không thay các điểm kiểm thử đã lưu |
| app/screens/xjtu.py | Hiển thị thực nghiệm, nguồn, biểu đồ và dự đoán XJTU riêng |
| notebooks/03_thuc_nghiem_xjtu.ipynb | Xem phân tích và chạy lại một vòng RF ngoài Streamlit |
| scripts/build_midterm.py | Sinh báo cáo tiến độ và 12 slide giữa kỳ 10/11/2026 |

XJTU có 6.961 chu kỳ hợp lệ. Chu kỳ đầu của mỗi pin đo ở 0,2C; 23 chu kỳ này được giữ trong bảng để đối chiếu nhưng không dùng cho đánh giá chính xả 1C. Có 6.938 chu kỳ trong kiểm thử mô hình.

`normalized_features` lấy 11 đặc trưng, bỏ giai đoạn, chia hai thống kê dòng điện cho dung lượng danh định (SDU 2,4 Ah; XJTU 2 Ah). Không chia cho dung lượng đo của chu kỳ vì đó là thông tin tạo nhãn. Các thống kê điện áp/nhiệt độ và số chu kỳ được giữ.

RF đa nguồn: trong mỗi vòng, tập học gồm SDU và các pin XJTU thuộc train; mỗi nguồn có tổng trọng số 0,5 để nguồn nhiều dòng không lấn hoàn toàn nguồn ít dòng. Tất cả pin XJTU test vẫn được giữ riêng. Cấu hình này có MAE 0,623, lớn hơn RF riêng XJTU 0,577 trong lần chạy; không kết luận thêm dữ liệu luôn tốt hơn.

Mô hình SDU chuyển trực tiếp sang XJTU sai số lớn. Dòng xả chuẩn hóa, độ lệch chuẩn và độ dốc điện áp XJTU đều ngoài khoảng SDU trong kiểm tra hiện tại. RF SDU 11 đặc trưng còn bỏ phase_code, nên so sánh với RF SDU nguyên bản không tách riêng tác dụng chuẩn hóa dòng. Điểm XJTU và SDU không được so sánh như cùng một bộ test.
