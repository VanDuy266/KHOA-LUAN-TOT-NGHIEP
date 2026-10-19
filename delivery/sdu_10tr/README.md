# SDU — 10 triệu dòng

10.000.000 dòng đo xả, đủ 20.823 chu kỳ tham chiếu và 86 pin. Giữ toàn bộ điểm 120 giây đầu và điểm cuối mỗi chu kỳ; chỉ giảm mật độ ở đoạn sau. Dòng được chọn giữ nguyên văn từ nguồn; không sửa số đo. Bộ lớn giữ riêng để đối chiếu.

## Tải về

Tải tất cả các phần dưới đây, giải nén vào cùng một thư mục. Mỗi phần là ZIP độc lập; chấp nhận ghi đè các file metadata giống nhau. Các file đo được chia giữa các phần, không trùng nhau. Cần đủ các phần để có đủ 10 triệu dòng.

- [Phần 1 — 88.7 MB](Dataset_SDU_10tr_phan_01.zip?raw=true)
- [Phần 2 — 88.8 MB](Dataset_SDU_10tr_phan_02.zip?raw=true)
- [Phần 3 — 88.8 MB](Dataset_SDU_10tr_phan_03.zip?raw=true)
- [Phần 4 — 82.0 MB](Dataset_SDU_10tr_phan_04.zip?raw=true)

Bảng training_table.csv vẫn giữ đủ 20.823 hàng như bộ 30,9 triệu dòng. Đọc dữ liệu đo từng file/khối, không nạp tất cả vào RAM.

Có 79 điểm nghi vấn tín hiệu trong bộ lớn chưa xác nhận là lỗi; danh sách kèm theo để kiểm tra, không tự sửa hoặc gọi là đã loại hết nhiễu. Chưa áp dụng dataset này vào ứng dụng hoặc chạy mô hình mới.

Nguồn: https://zenodo.org/records/14859405 — DOI 10.5281/zenodo.14859405, CC BY 4.0.

## Kết quả kiểm tra thực tế

- 10 triệu dòng, 20.823 chu kỳ và 86 pin; không thiếu/vô hạn ở tín hiệu chính, không có bản ghi trùng hoặc khóa thời gian trùng.
- Đặc trưng và dung lượng tham chiếu khớp bộ đầy đủ cho tất cả chu kỳ.
- Còn 25 điểm từ danh sách nghi vấn xung đơn, tất cả sau 120 giây. Chưa tự sửa/xóa hoặc gọi là hết nhiễu.
- Giữ nguyên thứ tự nguồn; có 23 bước thời gian đi lùi, được sắp xếp trên bản sao khi tính đặc trưng.

Xem [kết quả kiểm tra](KET_QUA_KIEM_TRA.md) và [nguồn/trích dẫn](NGUON_DU_LIEU.md). Các hồ sơ này có trong cả bốn gói ZIP.
