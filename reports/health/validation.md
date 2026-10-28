# Kiểm chứng dự báo xuống ngưỡng SOH — thử nghiệm



Mốc cơ sở: hồi quy tuyến tính OLS trên tối đa 20 mốc gần nhất. Không phải mô hình dự báo sự cố pin. Mốc 80% là tiêu chí nghiên cứu minh họa, không phải giới hạn an toàn của hãng.

Mỗi lịch sử được cắt tại 60%, 70%, 80% số mốc; chỉ phần trước mốc cắt dùng fit. Phần sau chỉ dùng đối chiếu. Không dùng giá trị tương lai khi tính đường dự báo. Không chọn mô hình/siêu tham số theo kết quả này.

Chỉ ngoại suy khi độ dốc âm, R² fit ít nhất 0,3, đường fit hiện tại trên ngưỡng và điểm giao không quá 3 lần khoảng lịch sử fit. Các quy tắc này cố định trước khi chạy, là giới hạn mô hình chứ không phải tiêu chí an toàn.



| Bộ dữ liệu | Mốc đánh giá | Có ngoại suy | Chạm ngưỡng tương lai quan sát được | Chạm ngưỡng có dự báo để chấm | Chưa quan sát chạm ngưỡng | MAE thời điểm (đơn vị) |

|---|---:|---:|---:|---:|---:|---|

| BMS | 60 | 52 | 44 | 42 | 9 | 3.29 months |

| SDU | 516 | 137 | 258 | 137 | 0 | 27.67 cycles |



Điểm chạm tham chiếu là mốc quan sát đầu tiên <=80%, không nội suy; lịch sử không chạm ngưỡng được coi là bị kiểm duyệt phải, không gán ngày hỏng. Lịch sử đã từng chạm trước mốc cắt bị loại khỏi đánh giá sự kiện tương lai. Sai số chỉ trên trường hợp vừa quan sát được chạm vừa có dự báo; không đại diện toàn bộ nhóm. Nhiều mốc cắt cùng pin/xe có phụ thuộc, không phải mẫu độc lập.

SDU tính theo chu kỳ; BMS tính theo tháng, không so trực tiếp hai MAE. BMS dùng nhãn xe–tháng suy ra từ dòng điện/SOC và có thể tổng hợp các phiên muộn hơn trong cùng tháng, nên chỉ là kiểm chứng hồi cứu, không khẳng định triển khai thời gian thực. Chưa có khoảng dự đoán được hiệu chuẩn; kết quả là ngoại suy thử nghiệm cần kiểm chứng ngoài tập này.

Không dùng kết quả để kết luận pin tốt/xấu, an toàn, hỏng/không hỏng hoặc ngày xảy ra sự cố. Chẩn đoán lỗi cần dữ liệu lỗi đã xác minh mà bộ dữ liệu hiện tại chưa có.

Phương pháp OLS: https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html . Phân biệt dự báo tuổi thọ tới mốc dung lượng với chẩn đoán lỗi: https://data.nasa.gov/dataset/li-ion-battery-aging-datasets .

Tái lập: .venv/Scripts/python.exe scripts/evaluate_health.py; chi tiết từng mốc cắt: chronological_results.csv.