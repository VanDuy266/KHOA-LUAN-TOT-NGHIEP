"""Phiếu HTML tự chứa và lịch sử trong phiên; không ghi dữ liệu upload ra đĩa."""

from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo
import pandas as pd


def current_time():
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%d/%m/%Y %H:%M:%S")


def add_history(history, rows, request_id, source, created_at):
    """Một yêu cầu chỉ ghi một lần; lịch sử giữ tối đa 500 chu kỳ gần nhất."""
    kept = [row for row in history if row["request_id"] != request_id]
    for row in rows.to_dict("records"):
        kept.append(
            {
                **row,
                "created_at": created_at,
                "source": source,
                "request_id": request_id,
            }
        )
    return kept[-500:]


def html_report(rows, created_at, source):
    from labels import vietnamese_table

    # pandas escape=True và html.escape bảo vệ tên file/mã pin do người dùng nhập.
    shown = vietnamese_table(rows).round(3)
    table_html = shown.to_html(index=False, border=0, escape=True, na_rep="—")
    return f"""<!doctype html><html lang="vi"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vincent D · Phiếu kết quả SOH</title><style>
body{{font-family:Arial,Helvetica,sans-serif;color:#193431;max-width:1100px;margin:45px auto;padding:0 25px;font-size:14px;line-height:1.6}}
header{{border-bottom:3px solid #087f70;padding-bottom:20px;margin-bottom:25px}}h1{{font-size:28px;margin:6px 0}}small{{color:#66766d}}
table{{width:100%;border-collapse:collapse;font-size:12px}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #dce4dc;overflow-wrap:anywhere}}th{{background:#edf3ec}}
.meta{{background:#f2f5ef;padding:18px;margin-bottom:22px}}footer{{margin-top:30px;border-top:1px solid #dce4dc;padding-top:15px;font-size:12px}}
@media print{{body{{margin:0;max-width:none;padding:0}}table{{font-size:10px}}tr{{break-inside:avoid}}@page{{size:A4 landscape;margin:15mm}}}}
</style><header><small>VINCENT D / PHÂN TÍCH PIN</small><h1>Phiếu kết quả ước lượng SOH</h1>
Nguyễn Văn Duy · MSSV 2311553949 · Khoa Học Dữ Liệu</header>
<div class="meta">Thời điểm: {escape(created_at)} (UTC+7)<br>Nguồn đầu vào: {escape(source)}<br>
Mô hình: Random Forest · Cửa sổ: 120 giây đầu chu kỳ xả · Dung lượng tham chiếu: 2,4 Ah</div>
{table_html}<footer>Kết quả từ mô hình nghiên cứu trên 86 cell SDU trong phòng thí nghiệm. SOH là tỷ lệ dung lượng, không phải mức sạc SOC.
Mẫu có sẵn thuộc dữ liệu đã dùng huấn luyện.</footer></html>"""
