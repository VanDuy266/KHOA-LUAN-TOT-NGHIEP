# Sức khỏe, số phiên sạc, dự báo ngưỡng và dấu hiệu lỗi

## Chức năng và phạm vi

- SOH và mức suy giảm: mô hình SOH đã có; trang sức khỏe dùng lịch sử SOH tham chiếu SDU hoặc nhãn suy ra BMS, không phải dự đoán SOH mới từ tín hiệu thô.
- SOC: lấy từ tín hiệu BMS ở kết quả BMS; trang lịch sử chỉ hiển thị SOC nếu CSV có soc_pct. Không suy SOC từ SOH.
- Số lần sạc: đếm phiên BMS đủ điều kiện trong lịch sử đến mốc chọn, không phải mọi lần cắm sạc hay tổng vòng đời. SDU hiển thị số chu kỳ quan sát, không xem là nhật ký sạc đầy đủ. Không có đủ dòng điện liên tục để tính equivalent full cycles cho toàn đời pin.
- Tuổi thọ tới ngưỡng: hồi quy tuyến tính OLS cố định trên tối đa 20 mốc gần nhất, ngưỡng người dùng chọn; 80% chỉ là mặc định minh họa, không ngưỡng hỏng của hãng. Quy tắc R² và độ dài ngoại suy là chất lượng mô hình, không tiêu chí an toàn. Đánh giá cắt lịch sử tại 60/70/80%, không đưa tương lai vào fit; xem reports/health/validation.md. Không đổi chu kỳ/tháng thành ngày hỏng.
- Lỗi pin: thực nghiệm độc lập từ Zenodo 18505707 v1 (CC BY 4.0), không ghép nhãn với SDU/BAIC. Random Forest binary baseline phân biệt lớp nguồn 0 và nhóm 1–4; không tự đặt ánh xạ tên từng loại lỗi. Đầu vào 50 hàng × 14 cột điện áp mV, cần dữ liệu đúng miền. Không dùng CSV BMS max/min để gọi mô hình này.

## Nguồn lỗi mới và kiểm chứng

Nguồn: https://zenodo.org/records/18505707 ; tác giả J. Li, Y. Che, S. Onori, W. Li, X. Hu, Decoupling battery faults from sparse voltage snapshots via cross-modal topology. Bản v1 công khai; bản v2 bị hạn chế và không được truy cập. README nguồn được giữ tại data/fault/extracted/Data & Code/readme.txt. MD5 gói v1 190be964af39615428834747654e853f, SHA256 trong reports/fault/summary.json. Mã nguồn tải về không được thực thi.

Nguồn mô tả điện áp xử lý từ 99 xe, nhãn quá mức không đồng nhất, tự xả bất thường, suy giảm dung lượng bất thường và ngắn mạch trong. Chưa xác minh mã 1–4 ứng với từng loại, vì vậy chỉ dùng nhóm nhị phân. Đọc thực tế 47.698 mẫu cell–snapshot; README ghi 47.968, khác 270 mẫu, không tự thêm mẫu. Mỗi CSV 50×14, nhãn đi kèm 14 cell; không xem 50 hàng là 50 chu kỳ sạc.

9 đặc trưng cố định/cell: trung bình, độ lệch chuẩn, min, max, range, độ dốc và trung bình biến thiên tuyệt đối của điện áp trừ trung vị cell cùng thời điểm; thêm trung bình/range điện áp gốc. Không đưa nhãn, số xe hay snapshot vào đầu vào. Không dùng scaler/global normalization. StratifiedGroupKFold 5 vòng seed 42 theo xe, không trùng xe, tham số RF cố định 120 cây/depth12/minleaf5/balanced_subsample; không tuning. Đây không phải tái hiện phương pháp cross-modal của bài nguồn.

Chỉ số pooled theo mẫu và độ nhạy báo cáo trong summary.json; các snapshot/cell cùng xe phụ thuộc, không thể coi hàng chục nghìn mẫu là độc lập. OOF đầy đủ trong oof_predictions.csv.gz, fold theo xe trong splits.json; chưa kiểm chứng trên đội xe bên ngoài. Ở kiểm thử đã lưu: TP 2.809, FN 87, FP 281, TN 44.521; precision khoảng 90,91%, recall 97,00%, F1 0,9385. Accuracy không đủ vì nhãn 0 chiếm đa số. Các mẫu minh họa được chọn có cả sai và đúng, không đại diện thống kê tần suất; bảng kiểm thử tính trên toàn bộ mẫu.

Kết luận sử dụng: “có dấu hiệu thuộc nhóm lỗi” hoặc “chưa phát hiện trong snapshot”. Không xác nhận hỏng/không hỏng vật lý, không chứng nhận an toàn và không dự báo thời điểm xảy ra sự cố. SOC, SOH, số lần sạc và nhãn lỗi không cùng tồn tại trên một xe chỉ vì lấy từ nhiều bộ dữ liệu.

## Tái lập và kiểm tra

Windows: chạy scripts/download_fault.py rồi scripts/build_fault.py bằng Python môi trường dự án; dữ liệu nguồn giữ nguyên. Chạy scripts/evaluate_health.py cho dự báo ngưỡng. Thông số cố định trước khi xem kết quả, thay đổi sau cần báo cáo thí nghiệm mới. Bộ kiểm thử gồm dữ liệu sai định dạng, SOC thiếu/ngoài phạm vi, số phiên sạc, kiểm tra cắt thời gian và đối chiếu mẫu OOF lỗi.
