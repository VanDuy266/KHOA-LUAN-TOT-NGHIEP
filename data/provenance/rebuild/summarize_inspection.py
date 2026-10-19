"""Tổng hợp kết quả kiểm tra; không áp dụng dữ liệu vào dự án."""
import json
from pathlib import Path
import pandas as pd

FOLDER=Path(__file__).resolve().parent
OUT=FOLDER/'inspection'


def number(value):return f'{value:,}'.replace(',','.')


def main():
    summaries=[json.loads((OUT/f'{phase}_summary.json').read_text()) for phase in ['Primary_use_phase','Second_life_phase']]
    identities=[pd.read_csv(OUT/f'{phase}_identities.csv') for phase in ['Primary_use_phase','Second_life_phase']]
    a,b=(set(frame.battery_id) for frame in identities)
    totals={key:sum(x[key] for x in summaries) for key in ['rows','csv_files','cycles','cycles_with_120s_voltage_current_temperature','cycles_without_complete_120s_window','missing_required_values','nonfinite_required_rows','exact_duplicate_rows','conflicting_time_keys','backward_time_rows','voltage_outside_0_5V_rows','temperature_outside_minus40_100C_rows','internal_resistance_missing_rows']}
    totals.update(unique_battery_ids=len(a|b),shared_battery_ids=len(a&b),source_doi='10.5281/zenodo.14859405',publication_date='2025-02-12',license='CC BY 4.0',applied_to_project=False)
    (OUT/'combined_summary.json').write_text(json.dumps(totals,ensure_ascii=False,indent=2))
    rows=['| Chỉ tiêu | Sử dụng ban đầu | Tái sử dụng |','| --- | ---: | ---: |']
    for key,label in [('csv_files','File CSV'),('rows','Dòng đo'),('distinct_battery_ids','Mã pin riêng biệt'),('cycles','Chu kỳ ghi nhận'),('cycles_with_120s_voltage_current_temperature','Chu kỳ có cửa sổ đầu xả đủ 120 giây theo kiểm tra'),('cycles_without_complete_120s_window','Chu kỳ chưa đạt tiêu chí cửa sổ xả đang kiểm tra'),('nonfinite_required_rows','Dòng thiếu hoặc vô hạn ở cột bắt buộc'),('exact_duplicate_rows','Dòng trùng hoàn toàn'),('conflicting_time_keys','Khóa thời gian xung đột'),('backward_time_rows','Thời gian đi lùi trong chu kỳ'),('voltage_outside_0_5V_rows','Điện áp ngoài miền kiểm tra 0–5 V')]:
        rows.append('| '+label+' | '+' | '.join(number(x[key]) for x in summaries)+' |')
    text='''# Kiểm tra bộ dữ liệu SDU 2025

## Nguồn

- Công trình: Deep sorting of reused batteries for enabling long-term consistency grouping with unknown prior conditions, Cell Reports Physical Science.
- Nguồn dữ liệu: https://zenodo.org/records/14859405
- DOI: 10.5281/zenodo.14859405. Công bố dữ liệu ngày 12/02/2025; không đồng nghĩa tất cả thí nghiệm được thực hiện năm 2025.
- Giấy phép: CC BY 4.0; cần ghi nguồn khi sử dụng.
- Theo tác giả: 86 cell Lishen LR1865SZ, NMC(532)/graphite, dung lượng danh định 2,4 Ah; thí nghiệm kéo dài 30 tháng, gồm giai đoạn sử dụng ban đầu và tái sử dụng.

## Kết quả kiểm tra toàn bộ CSV

'''+ '\n'.join(rows)+f'''

Tổng cộng {number(totals['rows'])} dòng đo, {number(totals['cycles'])} chu kỳ ghi nhận và {number(totals['csv_files'])} file CSV. Hai giai đoạn có {len(a&b)} mã pin chung; tổng số mã pin riêng biệt là {len(a|b)}, không cộng hai giai đoạn thành 172 pin độc lập.

Các cột bắt buộc đã kiểm tra: thời gian, chu kỳ, dòng điện, điện áp, dung lượng sạc/xả, nhiệt độ bề mặt, mã pin và giao thức. Mã MD5 của cả hai ZIP khớp với bản công bố trên Zenodo. Đọc hết từng CSV cũng kiểm tra CRC của các mục ZIP được đọc.

## Các bất thường đã xác định

- Có 138 bước thời gian đi lùi trong thứ tự dòng gốc. Chưa phát hiện khóa thời gian trùng sau khi kiểm tra, nên cần kiểm tra thứ tự và sắp xếp trong từng pin/chu kỳ trước khi tính đặc trưng.
- Có 2 dòng điện áp 5,506171 V tại Second_life_phase/85.csv, Battery_ID 79, chu kỳ 509, bước 22 và 23. Đây là giá trị bất thường đối với cell NMC, cần loại hoặc xác minh từ tác giả; không tự sửa thành giá trị mong muốn.
- Giai đoạn đầu có 8 chu kỳ dung lượng dưới 0,5 Ah; giai đoạn tái sử dụng có 1 chu kỳ dưới 0,5 Ah. Chỉ ghi nhận để kiểm tra, không tự coi dung lượng thấp là lỗi hoặc tự loại theo ngưỡng này. Dung lượng thấp ở giai đoạn tái sử dụng có thể phản ánh suy giảm thật.

## Những điểm cần xử lý trước khi huấn luyện

1. Điện trở trong thưa theo thời điểm đo: {number(totals['internal_resistance_missing_rows'])} dòng để trống. Đây không phải lý do loại toàn bộ các dòng này; không coi điện trở là tín hiệu có ở mọi thời điểm và không tự điền số giả.
2. Chu kỳ vận hành và chu kỳ chẩn đoán có chế độ xả khác nhau. Trong file mẫu Primary_use_phase/1.csv, chu kỳ 1 và 6 có dòng xả trung vị khoảng -0,48 A, điện áp cuối khoảng 3 V; các chu kỳ vận hành xen kẽ khoảng -2,4 A, điện áp cuối khoảng 2 V. Cần phân loại bằng giao thức và tín hiệu, không lấy dung lượng của mọi chu kỳ làm nhãn SOH tương đương.
3. Dung lượng danh định tham khảo theo tác giả là 2,4 Ah. Chỉ chốt nhãn SOH sau khi xác định đúng chu kỳ đo dung lượng tham chiếu và kiểm tra mức độ hoàn tất chu kỳ. Số chu kỳ ghi nhận chưa phải số mẫu học máy cuối cùng.
4. Chỉ số chu kỳ khởi động lại ở giai đoạn tái sử dụng. Khóa dữ liệu cần gồm giai đoạn, Battery_ID và Cycle_Index. Khi đánh giá pin chưa thấy, phải chia theo Battery_ID vật lý qua cả hai giai đoạn để tránh cùng pin xuất hiện trong tập học và tập kiểm thử.
5. Có giao thức xả xung: kiểm tra file Primary_use_phase/81.csv cho thấy đoạn xả đầu khoảng 50 giây, tiếp theo nghỉ rồi xả lại. Vì vậy, không đạt tiêu chí xả liên tục 120 giây không đồng nghĩa file hỏng; cần thiết kế đặc trưng theo giao thức hoặc dùng chu kỳ chẩn đoán thống nhất. Những trường hợp không đạt phải được ghi nhật ký, chưa tự nội suy hoặc nhân bản. Điều kiện kiểm tra hiện tại: ít nhất 5 mẫu xả trong 120 giây đầu, trải dài ít nhất 90 giây, có đủ điện áp/dòng/nhiệt độ hữu hạn, không trùng thời gian trong cửa sổ. Kiểm tra này chỉ xét các mẫu có dòng xả, nên có thể không phù hợp trực tiếp với giao thức xả xung. Ngưỡng xả dùng trong kiểm tra là dòng < -0,01 A; cần xác nhận theo giao thức trước khi chốt đặc trưng.
6. Dung lượng dương chưa chứng minh chu kỳ xả hoàn tất. Bộ ban đầu có giá trị nhỏ tới khoảng 0,0073 Ah; cần xem chu kỳ bị ngắt hoặc giai đoạn đo trước khi tạo nhãn. Không gọi đây là SOH thực tế rất thấp khi chưa xác minh.
7. Tên file không phải Battery_ID. Theo tác giả, pin mang số tên file 61 và 62 không có dữ liệu do hư hỏng thí nghiệm. Mã Battery_ID trong CSV dùng để đối chiếu với bài báo.

## Đánh giá mức phù hợp

SDU có các tín hiệu cần cho phân tích và dự đoán SOH, nhiều pin, dữ liệu suy giảm qua hai giai đoạn và nguồn công bố năm 2025. Bộ này phù hợp để xây dựng thực nghiệm hồi quy SOH sau khi chọn đúng nhãn và làm sạch các trường hợp đã nêu. Kiểm tra cấu trúc và giá trị không thay thế việc xác thực cảm biến hoặc tái lập thí nghiệm của tác giả.

Dữ liệu là thí nghiệm trên cell, chưa chứng minh mô hình hoạt động trên pack hoặc xe điện thực tế tại Việt Nam. Nếu giảng viên yêu cầu dữ liệu xe vận hành thực, bộ này chưa đáp ứng riêng tiêu chí đó.

Trạng thái: chỉ tải và kiểm tra. Chưa áp dụng SDU vào code, mô hình, giao diện hay GitHub của dự án.
'''
    (OUT/'KET_QUA_KIEM_TRA_SDU.md').write_text(text)
    print(json.dumps(totals,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
