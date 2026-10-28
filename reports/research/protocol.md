# Thực nghiệm bổ sung và cách tái lập

## 1. SHAP tổng hợp
CatBoost cuối cùng đang phục vụ, 516 mẫu: ba chu kỳ quan sát phân bố đều trong mỗi tổ hợp 86 pin × hai giai đoạn SDU. SHAP gốc CatBoost. Mẫu có tham gia học mô hình cuối; kết quả chỉ mô tả cách mô hình sử dụng đầu vào, không đánh giá tính chính xác ngoài tập học và không xác định nguyên nhân chai pin. Tái dựng baseline + tổng SHAP khớp đầu ra với sai lệch tối đa khoảng 6,4e-14 điểm %. CSV xếp hạng dùng trung bình |SHAP| trên mẫu cân bằng theo pin/giai đoạn. Màu trên biểu đồ là giá trị đầu vào tương đối của từng đặc trưng.

## 2. ICA / DVA
Sáu đoạn xả toàn chu kỳ của SDU_01: đầu, giữa và cuối mỗi giai đoạn. Q tích phân dòng xả âm theo thời gian /3600. Làm trơn điện áp Savitzky–Golay cửa sổ 21 điểm bậc 3; ICA nội suy lưới 10mV, làm trơn Q(V) 11 điểm; DVA lưới Q 200 điểm, làm trơn 11 điểm trước đạo hàm. Chỉ nhận đoạn có >=100 điểm, thời gian tăng không trùng, khoảng trống <=60s, CV dòng <=0,1, vùng điện áp >=0,3V và tỷ lệ bước đảo điện áp >1mV sau làm trơn <=10%. Đạo hàm đường xả có thể âm. Chưa đánh giá độ nhạy tham số làm trơn hoặc gán đỉnh cho cơ chế hóa học. Chỉ minh họa phân tích miền, KHÔNG đưa toàn chu kỳ vào predictor đầu xả 120 giây vì sẽ dùng thông tin tương lai.

## 3. Kiểm chứng NASA thật
Nguồn chính thức: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/ , mục 5 Batteries. Trích dẫn: B. Saha và K. Goebel (2007), Battery Data Set, NASA Ames Prognostics Data Repository. Lấy bốn file B0005/B0006/B0007/B0018 từ archive NASA dẫn đến PHM Society S3; không lấy nhãn từ bản mô phỏng hoặc repository có fallback giả lập.

SHA256 archive: 82302a7db4fc1b34e0b6676326610438d43b816bdf11a69d1d012a464ef2f92e. Hash từng MAT trong nasa_transfer.json. 636 chu kỳ xả được giữ, 0 chu kỳ bị loại bởi kiểm tra đầu vào 120 giây. Capacity nguồn chia 2 Ah ×100. README ghi điều kiện kết thúc xả khác nhau cho bốn pin; cột Capacity cũng có mô tả tham chiếu 2,7V, nên nhãn không mặc nhiên tương đương SDU. Không khẳng định cùng hóa học pin khi README chưa xác lập.

Bốn mô hình SDU giữ nguyên trọng số, không học từ nhãn NASA, kiểm thử zero-shot. phase_code=0 là quy ước; cycle là số thứ tự xả trong NASA. Hai trường này không bất biến miền. Dự đoán không cắt về [0,100], để giữ được bằng chứng ngoại suy thất bại.

NASA → NASA: RF cấu hình cố định từ RF hiện có, leave-one-cell-out bốn lượt. SDU + NASA → NASA: mỗi lượt gộp SDU và ba cell NASA train, thêm nominal_ah (SDU=2,4; NASA=2), giữ toàn bộ cell NASA còn lại làm test. Không điều chỉnh siêu tham số bằng nhãn cell test. Mô hình gộp có NASA trong train nên không phải kiểm thử nguồn hoàn toàn chưa biết; chưa đưa artifact thử nghiệm này vào ứng dụng dự đoán.

MAE/RMSE/R² tính theo từng cell rồi lấy trung bình đều bốn cell. Kết quả không dùng để chọn cấu hình bằng test, không suy rộng mọi pin hoặc hóa học khác. Khác dòng, nhiệt độ, điện áp cắt và định nghĩa nhãn có thể ảnh hưởng kết quả.

| Thiết kế | MAE macro (điểm % SOH) | Kết luận trong thí nghiệm |
|---|---:|---|
| SDU RF → NASA | 8,5964 | Chuyển miền kém |
| SDU CatBoost → NASA | 7,3349 | Vẫn sai số đáng kể |
| SDU XGBoost → NASA | 11,9552 | Chuyển miền kém |
| SDU Ridge–RF → NASA | 9850,9403 | Ngoại suy không phù hợp nghiêm trọng; không che số gốc |
| NASA RF → cell NASA giữ riêng | 2,7633 | Tốt hơn các mô hình chuyển thẳng trong bốn cell này |
| SDU + NASA RF → cell NASA giữ riêng | 3,1704 | Gộp chưa hơn NASA riêng |

Chưa thực nghiệm MIT, không gọi là mô hình mọi loại pin. Không suy lỗi/hỏng hoặc chứng nhận an toàn từ SOH. Nhãn lỗi vẫn là bài toán độc lập trên 99 xe khác.

## 4. Tái lập
Tại thư mục dự án:

```powershell
.venv/Scripts/python.exe scripts/download_nasa.py
.venv/Scripts/python.exe scripts/evaluate_nasa_transfer.py
.venv/Scripts/python.exe scripts/build_research_extensions.py
```

Tệp kết quả: shap_summary.json, shap_importance.csv, electrochemical_curves.json, nasa_features.csv, nasa_excluded.csv, nasa_predictions.csv, nasa_by_battery.csv, nasa_transfer.json. Không tải lại hoặc huấn luyện khi mở trang web; web chỉ đọc các báo cáo đã tính.
