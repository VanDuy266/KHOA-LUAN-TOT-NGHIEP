# Căn cứ đối chiếu sức khỏe bộ pin BAIC EU500

Ngày rà nguồn: 28/10/2026. Kết quả dưới đây phân biệt tiêu chí nghiên cứu với thông số chính hãng; không xác nhận an toàn một xe cụ thể.

## 1. Cấu hình đã xác minh

Tác giả bộ dữ liệu BatICM xác nhận 20 xe BAIC EU500, CATL NCM, 145 Ah, 90 cell nối tiếp và 32 cảm biến nhiệt. Nguồn: https://github.com/BatICM/battery-charging-data-of-on-road-electric-vehicles . README không công bố bộ ngưỡng chẩn đoán, mã BMS/phần mềm, VIN hay báo cáo an toàn từng xe. Đầu vào phân tích hiện có điện áp min/max, dòng, SOC, nhiệt độ min/max; chưa có điện áp định danh từng cell, mã lỗi, cách điện hoặc kiểm định vật lý.

## 2. Mốc dung lượng có thể áp dụng trong nghiên cứu

JRC EUR 29371 EN (2018), Standards for the performance and durability assessment of electric vehicle batteries, trình bày tiêu chí kết thúc thử nghiệm theo mức suy giảm còn 80% giá trị ban đầu trong một số phương pháp. Xem trang PDF 42–43 và 49 (trang in 39–40 và 46), phần vòng đời; nguồn đầy đủ: https://publications.jrc.ec.europa.eu/repository/bitstream/JRC113420/kjna29371enn.pdf .

Áp dụng trên web: mốc SOH 80% là tiêu chí tham khảo do nghiên cứu chọn. Phân loại chỉ cho biết SOH ước tính trên/dưới mốc, không có nghĩa đạt chuẩn hãng hoặc đã kiểm định theo quy trình JRC/SAE/USABC. SOH web tính theo 145 Ah danh định; tài liệu nói đến giá trị ban đầu/rated capacity theo từng phép thử, nên việc quy đổi sang mốc danh định là quy ước nghiên cứu cần công bố, không coi là phép thử chuẩn đã thực hiện.

Ngưỡng tùy chọn vẫn để trống cho tới khi người dùng áp dụng. Không dùng mốc dung lượng này để suy ra trạng thái lỗi hoặc an toàn.

## 3. Nhiệt độ và chênh điện áp

Chưa xác minh được giới hạn BMS chính hãng đúng bộ CATL NCM 145 Ah, 90S trong bộ dữ liệu. Cần tài liệu đặc tính cell/module, giới hạn vận hành bộ pin và bảng chẩn đoán đúng model/đời xe/phần mềm BMS; điều kiện SOC, dòng, nhiệt độ, thời gian duy trì và mức cảnh báo phải đi cùng giới hạn. Không dùng một giá trị nhiệt độ hoặc mV cho mọi cấu hình.

Nguồn chính hãng đã xem:
- BAIC EU5 Specifications (2022): https://www.baicglobal.com/file/upload/2022/08/12/EU5%20Specifications_20220812130509A021.pdf . Tài liệu công bố cấu hình PE0GU 48,3 kWh và điều kiện sạc ở 25°C; không công bố giới hạn an toàn nhiệt độ/chênh cell và không chứng minh bộ pin trùng mẫu nghiên cứu.
- Trung tâm sổ tay BAIC: https://www.baicglobal.com/news/multimedia . Có mục EU5 nhưng chưa đọc được nội dung giới hạn áp dụng; tải trực tiếp trả HTTP403, không truy cập vượt hạn chế.
- Tài liệu BAIC https://www.bjev.com.cn/bjev/202102/22/2c7b1649ea35462394f721619130939d.pdf có giới hạn 0–55°C nhưng áp dụng bộ Gotion LFP 135 Ah, 101S, model DJ1905, không phải CATL NCM 145 Ah 90S: loại khỏi tiêu chí.
- Bằng sáng chế CN115447439A: https://patents.google.com/patent/CN115447439A/zh mô tả một trường hợp EU5 2021 với giá trị nhiệt độ 55°C; đây là ví dụ của chủ sáng chế, không phải tài liệu đặc tính được BAIC/CATL xác nhận cho 20 xe. Chỉ lưu như đầu mối, không dùng làm mặc định.
- Sổ tay EU5 do đại lý đăng tại https://www.motornationmexicali.com.mx/static/agency-go-virtual/Motornation/Manuales_de_Propietario/Manuales_de_Propietario_BAIC/Manual_del_propietario_BAIC_EU5_compressed.pdf chưa truy xuất được (HTTP403), không suy diễn nội dung.

## 4. Lỗi và an toàn: bằng chứng còn thiếu trên chính xe BAIC

Để xác nhận một lỗi cụ thể cần mã lỗi đang hoạt động, dữ liệu liên quan cùng thời điểm, đúng định nghĩa mã lỗi và bước kiểm tra xác nhận. Kết luận an toàn còn cần kiểm tra phù hợp tình trạng xe như cách điện cao áp, bảo vệ, cảm biến, hư hại cơ học và thử nghiệm do cơ sở có chuyên môn thực hiện; danh sách kiểm tra cụ thể phải theo quy trình đúng cấu hình. Không có mã lỗi không chứng minh không lỗi; một cửa sổ đầu sạc 120 giây không loại trừ mọi sự cố.

Bộ Zenodo 18505707 có nhãn lỗi và đã dùng trong mục Dấu hiệu lỗi pin: https://zenodo.org/records/18505707 . Đó là 99 xe ẩn danh khác; dữ liệu là 50×14 điện áp mV đã xử lý, không có định danh liên kết tới BAIC_01…20. Không thể gắn nhãn của xe khác sang xe BAIC để lấp ô chưa xác định. Mô hình có báo nhầm/bỏ sót, không thay thế kiểm định.

## 5. Kết quả rà nguồn

| Hạng mục | Có thể xác định hiện tại | Phần chưa có |
|---|---|---|
| Dung lượng | SOH ước tính, mức chai, trên/dưới mốc tham khảo được chọn | Dung lượng RPT độc lập của chính xe |
| Tín hiệu | Số đo nhiệt độ và chênh cell; đối chiếu khi có tiêu chí kèm nguồn | Giới hạn hãng đúng bộ pin và điều kiện áp dụng |
| Lỗi | Phân loại nghiên cứu trên bộ điện áp có nhãn riêng | Chẩn đoán lỗi xác nhận trên chính xe BAIC |
| An toàn | Ghi rõ chưa có xác nhận | Kết quả kiểm tra kỹ thuật và quy trình đánh giá đúng xe |

Không tự nhập 45/55°C, 30/50 mV hay mốc 80% như một bộ tiêu chuẩn an toàn chung. Các trường chưa đủ bằng chứng vẫn phải ghi chưa xác định.
