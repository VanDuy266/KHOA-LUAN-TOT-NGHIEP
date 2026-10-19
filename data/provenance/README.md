# Hồ sơ nguồn SDU

Các CSV/JSON trong thư mục này ghi lại nguồn, ngân sách chọn theo chu kỳ, dấu vân tay nội dung và kết quả kiểm tra. Các file `.csv.gz` nguyên dòng được phát riêng trên nhánh `dataset-sdu-10tr`; sản phẩm dùng bản Parquet dẫn xuất để đọc nhanh.

## Tái tạo từ gói tác giả

`rebuild/` giữ cấu trúc thư mục của quy trình tạo bộ chọn. Đây là bước xử lý nguồn lớn, không cần chạy khi mở ứng dụng hoặc chạy lại mô hình từ dữ liệu đã chuẩn bị.

Tại `rebuild/`, có metadata `zenodo_record.json`. Quy trình lần lượt:

```text
python download_sdu.py
python inspect_sdu.py
python summarize_inspection.py
python selection/select_sdu.py
python selection/preserve_source_rows.py
python quality_review/check_noise.py
python ten_million/build_10m.py
```

Các script có vị trí đầu ra tương đối theo thư mục chứa file. `download_sdu.py` tải khoảng 4,49 GB ZIP gốc và xác nhận MD5. Các bước sau cần thêm dung lượng đĩa cho bộ xả đầy đủ và các bản dẫn xuất; có thể cần hàng chục GB trống. Cần giữ các thư mục `selection`, `quality_review` và `ten_million` cùng cấp, cùng hai ZIP nguồn và metadata.

Không cần tái tạo bước này để dùng bộ 10 triệu dòng đã nhận. Quy trình chuẩn của sản phẩm bắt đầu từ `scripts/download_data.py --zip ...`, rồi `prepare_data.py`. Mọi dòng nguồn được chọn giữ nguyên; biểu diễn chuẩn hóa hoặc nội suy cho GRU chỉ nằm ở dữ liệu dẫn xuất riêng.

Phiên bản hiện tại có 10.505.065 dòng. Bước lấy thưa dùng `scripts/build_reference_subset.py --parent <selection> --reference <hồ_sơ_SDU> --output <thư_mục_mới>`, giữ các điểm bắt buộc và mỗi ba điểm còn lại một điểm. Script build_10m.py lưu ở rebuild là phương án ngân sách cũ; không dùng để tạo bản hiện tại.
