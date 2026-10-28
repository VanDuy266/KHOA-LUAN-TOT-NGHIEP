# Dữ liệu pin bên ngoài

Tên đề tài giữ nguyên: Phân tích và dự đoán tình trạng sức khỏe pin xe điện bằng các mô hình học máy. Hồi quy SOH trên SDU và BAIC là phần chính. Bộ tiếp nhận ngoài nguồn là chức năng mở rộng, không biến mô hình thành bộ dự đoán cho mọi pin.

## Luồng sử dụng
Kiểm tra pin → Phân tích dữ liệu bên ngoài → tải file → xem trước → khai báo cấu hình → chọn cột/đơn vị → phân tích tín hiệu.

Nhận CSV, CSV.GZ và JSON là mảng bản ghi phẳng; CSV/CSV.GZ tối đa 512 MiB tải lên, 1 GiB sau giải nén khi đọc từng khối; JSON tối đa 20 MiB. Giữ tối đa 100.000 dòng của nhóm đã chọn, quét tối đa 10 triệu dòng. Không nhận JSON lồng nhau, XLSX hoặc MAT ở luồng này. MAT NASA được xử lý bởi script nghiên cứu riêng, không có nghĩa web đọc mọi cấu trúc MAT.

## Cấu hình và tín hiệu
Khai báo hóa học (hoặc chưa rõ), cell/bộ pin, sạc/xả/hỗn hợp và dung lượng định mức nếu biết. Ánh xạ thời gian dạng số, điện áp, dòng điện, nhiệt độ; SOC phần trăm là tùy chọn. Chọn rõ đơn vị và dấu dòng xả. Không đổi tên điện áp pack thành điện áp cell hoặc suy SOC từ SOH. Mỗi file chỉ gồm một đoạn của cùng pin, thời gian tăng không trùng; mốc đầu được quy về 0.

## Kết quả có thể trả
Điện áp nhỏ/lớn nhất, nhiệt độ nhỏ/lớn nhất, SOC cuối nếu được cung cấp, độ dài đoạn và điện lượng nạp/xả trong đoạn. Tích phân hình thang theo dòng điện và thời gian; quy ước dòng xả âm. Không tích phân nếu có khoảng trống đo >60 giây. JSON tải về chứa hồ sơ, kết quả, cảnh báo và SHA256 dữ liệu đầu vào. Không lưu file người dùng lên kho dữ liệu hoặc tự dùng file đó để huấn luyện.

Điện lượng của một đoạn không phải dung lượng đầy. Không lấy điện lượng đoạn / dung lượng định mức để xuất SOH; không coi SOH là SOC.

## Chọn phương pháp tiếp theo
- Có dung lượng xả đo đầy đủ và mốc ban đầu cùng điều kiện: dùng trang tính tỷ lệ dung lượng.
- Khai báo NMC, một cell, xả, 2,4 Ah: chỉ cho mở bước xác nhận thủ công dữ liệu đúng phạm vi SDU rồi chuyển file. Trùng hồ sơ KHÔNG tự chứng minh cùng phân phối hoặc chính xác; kiểm tra tín hiệu và miền đặc trưng vẫn được thực hiện ở mô hình.
- BAIC EU500 145 Ah có đủ tám tín hiệu cần thiết: dùng chức năng BMS riêng.
- Cấu hình khác: phân tích số liệu đo; chưa xuất SOH bằng mô hình SDU. Muốn đưa mô hình mới vào phục vụ cần dữ liệu nhãn, chia nhóm, kiểm thử ngoài tập học và metadata nguồn.

Hỏng/an toàn cần chẩn đoán phù hợp và đối chiếu thực tế; thống kê tín hiệu hoặc dung lượng đơn thuần không chứng nhận an toàn. Các cảnh báo nhập liệu trong phần này không phải mã lỗi của nhà sản xuất.


## File nhiều pin hoặc chu kỳ
Xem trước chỉ đọc 5 dòng. Chọn cột mã pin, chu kỳ và giai đoạn nếu file chứa nhiều nhóm, rồi nhập giá trị cần phân tích. Các nhóm còn lại không được giữ trong bộ nhớ. Mã pin, số chu kỳ hợp lệ và phase_code được bảo toàn trong CSV chuẩn hóa để tránh dùng nhầm mặc định ở mô hình. JSON lớn nên đổi sang CSV. Các endpoint dự đoán trực tiếp vẫn giới hạn 20 MiB; dùng bộ tiếp nhận file lớn để lọc trước.
