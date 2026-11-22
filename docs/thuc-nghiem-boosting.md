# Thực nghiệm CatBoost và XGBoost trên SDU

## Dữ liệu và giao thức

Dùng 20.823 chu kỳ SDU từ 86 pin vật lý, 12 đặc trưng và năm vòng kiểm thử theo pin đã lưu. Trong mỗi vòng, giữ riêng 20% nhóm của tập học cho validation. Với mỗi mô hình, thử ba mức độ sâu. Số cây được chọn theo RMSE validation với dừng sớm, cấu hình được chọn theo MAE trung bình theo pin trên validation. Sau đó huấn luyện lại trên toàn bộ tập học của vòng và dự đoán pin giữ riêng. [Phân hoạch SDU](../reports/split_assignments.csv) · [Thông số và phiên bản](../reports/boosting/metadata.json)

## Kết quả

MAE và RMSE tính theo điểm phần trăm SOH. Mỗi pin có cùng trọng số trong phép tổng hợp.

| Mô hình | MAE | RMSE | R² |
| --- | ---: | ---: | ---: |
| CatBoost | 1,677 | 2,188 | 0,9696 |
| XGBoost | 1,692 | 2,212 | 0,9692 |

SOH ước lượng bằng CatBoost có MAE thấp hơn Random Forest trên 37/86 pin, XGBoost trên 27/86 pin. Trung bình theo pin, MAE của CatBoost và XGBoost cao hơn Random Forest lần lượt 0,058 và 0,073 điểm phần trăm SOH. Random Forest đạt MAE 1,619 và Ridge–RF đạt 1,612. So sánh phản ánh cả thuật toán lẫn ngân sách dò cấu hình trên SDU. Hai mô hình boosting này chưa được đánh giá trên BAIC. [Bảng chỉ số](../reports/boosting/metrics_summary.csv.gz) · [So sánh ghép cặp](../reports/boosting/paired_comparison.csv.gz)

## Tái lập

Cài phụ thuộc theo `requirements-render.txt` trên Python 3.12. Từ gốc dự án, chạy `python scripts/evaluate_boosting.py` trong môi trường đã kích hoạt. Script đọc các bảng SDU đã đóng gói và ghi kết quả vào `reports/boosting/`, mô hình huấn luyện lại vào `artifacts/boosting/`. Giữ bản sao kết quả trước khi chạy lại nếu cần đối chiếu số liệu. Mô hình huấn luyện lại phục vụ suy luận. Bảng điểm dùng kết quả dự đoán pin giữ riêng. [Mã thực nghiệm](../scripts/evaluate_boosting.py) · [CatBoost](https://proceedings.neurips.cc/paper/2018/hash/14491b756b3a51daac41c24863285549-Abstract.html) · [XGBoost](https://arxiv.org/abs/1603.02754)
