# Phạm vi đề tài và ba nguồn dữ liệu đang sử dụng

Đề tài: Phân tích và dự đoán tình trạng sức khỏe pin xe điện bằng các mô hình học máy.

## Kết quả chính

Ước tính sức khỏe dung lượng SOH và mức suy giảm dung lượng. Đánh giá mô hình bằng MAE, RMSE và R² trên pin/xe giữ riêng. Không xem R² hay SOH là xác suất pin hỏng hoặc mức an toàn.

| Nguồn | Đối tượng | Nhiệm vụ | Căn cứ kết quả |
|---|---|---|---|
| SDU | 86 tế bào pin, hai giai đoạn | SOH và mức chai từ 120 giây đầu xả | Dung lượng xả nguồn / 2,4 Ah; kiểm thử 5 vòng theo pin |
| BAIC/BatICM | 20 xe EU500, bộ pin 145 Ah | Kiểm chứng SOH vận hành, tín hiệu sạc và số phiên đủ điều kiện | Nhãn dung lượng suy ra từ dòng điện/SOC; kiểm thử 5 vòng theo xe |
| Zenodo 18505707 v1 | 99 xe ẩn danh khác | Mở rộng: phân loại dấu hiệu lỗi từ điện áp | Nhãn 0 và nhóm 1–4 từ nguồn; kiểm thử 5 vòng theo xe |

## Các phần mở rộng

Dự báo ngưỡng dung lượng dùng lịch sử SDU hoặc BAIC của đúng một đối tượng đã chọn; đây là ngoại suy xu hướng thử nghiệm, không phải dữ liệu thứ tư và không phải dự báo mọi sự cố.

Phân loại lỗi dùng bộ Zenodo riêng. Khi xem mẫu có nhãn, nhãn nguồn và dự đoán được hiển thị riêng để kiểm tra cả cell phát hiện, bỏ sót và báo nhầm. CSV mới không có nhãn chỉ nhận kết luận dự đoán của mô hình. Các nhãn không chứng nhận an toàn tuyệt đối.

## Phần không được gộp

BAIC_01 không phải xe 0 của Zenodo. Không suy nhãn lỗi của bộ này cho đối tượng bộ khác; không cộng số pin/xe thành một đoàn xe đồng nhất. Số lần sạc chỉ là số phiên đủ điều kiện đã quan sát, không phải tổng cả vòng đời. SOH/SOC, số phiên và kết quả lỗi chưa đồng thời có trên cùng một đối tượng trong cả ba nguồn.

XJTU và các thư mục sao lưu không nằm trong ba nguồn dùng bởi web hiện tại. Demo pin giữ riêng SDU_01 là một phép kiểm thử của SDU, không phải dataset mới.

## Trình bày phạm vi khi bảo vệ

SOH và mức chai là mục tiêu chính. Dữ liệu BAIC là kiểm chứng vận hành với nhãn suy ra, có giới hạn riêng. Ngoại suy ngưỡng và phân loại lỗi là các thực nghiệm mở rộng, được công bố độc lập; không dùng chúng thay bằng chứng của phần SOH.
