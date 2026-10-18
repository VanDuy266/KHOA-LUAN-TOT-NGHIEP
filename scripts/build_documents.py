"""Build an evidence-based Markdown report, editable Word file and slides."""
import re
from pathlib import Path
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.shared import Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from pptx import Presentation
from pptx.util import Inches as PptInches, Pt as PptPt

ROOT = Path(__file__).resolve().parents[1]


def md_table(frame):
    def fmt(value):
        return f"{value:.3f}" if isinstance(value, float) else str(value)
    return "\n".join(["| " + " | ".join(frame.columns) + " |",
        "| " + " | ".join(["---"] * len(frame.columns)) + " |"] +
        ["| " + " | ".join(fmt(v) for v in row) + " |" for row in frame.itertuples(index=False, name=None)])


def main():
    summary = pd.read_csv(ROOT / "reports/metrics_summary.csv")
    by_battery = pd.read_csv(ROOT / "reports/metrics_by_battery.csv")
    audit = pd.read_csv(ROOT / "reports/data_audit.csv")
    template = (ROOT / "docs/bao-cao-template.md").read_text(encoding="utf-8")
    text = template.replace("{{SUMMARY_TABLE}}", md_table(summary))
    text = text.replace("{{BY_BATTERY_TABLE}}", md_table(by_battery))
    text = text.replace("{{AUDIT_TABLE}}", md_table(audit))
    rf = summary[summary.model == "Random Forest"].iloc[0]
    cycle = summary[summary.model == "Cycle Ridge"].iloc[0]
    replacements = {
        "{{RF_MAE}}": f"{rf.mae:.3f}", "{{RF_RMSE}}": f"{rf.rmse:.3f}",
        "{{CYCLE_MAE}}": f"{cycle.mae:.3f}",
        "{{MAE_REDUCTION}}": f"{100 * (cycle.mae - rf.mae) / cycle.mae:.1f}",
        "{{ABLATION_TABLE}}": md_table(pd.read_csv(ROOT / "reports/ablation_summary.csv")),
        "{{TEMPORAL_TABLE}}": md_table(pd.read_csv(ROOT / "reports/temporal_metrics.csv")),
        "{{DATA_DICTIONARY}}": (ROOT / "data/README.md").read_text(encoding="utf-8").split("## Từ điển cột bảng toàn bộ phép đo\n\n")[1].split("\n\nKhông dùng")[0],
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    if "{{" in text:
        raise ValueError("Báo cáo còn trường chưa được điền từ kết quả")
    (ROOT / "docs/bao-cao-khoa-luan.md").write_text(text, encoding="utf-8")
    doc = Document()
    doc.styles["Normal"].font.name = "Times New Roman"
    doc.styles["Normal"].font.size = Pt(13)
    doc.styles["Normal"].paragraph_format.line_spacing = 1.5
    section = doc.sections[0]
    section.left_margin, section.right_margin = Cm(3.5), Cm(2)
    section.top_margin, section.bottom_margin = Cm(2.5), Cm(2.5)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    doc.settings.element.append(update)
    table_lines = []

    def flush_table():
        if not table_lines:
            return
        rows = [[c.strip() for c in line.strip("|").split("|")] for line in table_lines]
        rows = [row for row in rows if not all(re.fullmatch(r":?-+:?", c) for c in row)]
        table = doc.add_table(rows=0, cols=len(rows[0]))
        table.style = "Table Grid"
        for row in rows:
            cells = table.add_row().cells
            for cell, value in zip(cells, row):
                cell.text = value
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(9)
        table_lines.clear()

    for line in text.splitlines():
        if line.startswith("|"):
            table_lines.append(line)
            continue
        flush_table()
        if not line.strip():
            continue
        image = re.fullmatch(r"!\[(.*?)\]\((.*?)\)", line)
        if image:
            path = ROOT / "docs" / image.group(2)
            doc.add_picture(str(path.resolve()), width=Cm(15.5))
            doc.add_paragraph(image.group(1))
        elif line.startswith("#"):
            prefix, title = line.split(" ", 1)
            if title == "Tóm tắt":
                doc.add_page_break()
                doc.add_heading("Mục lục", level=1)
                toc = OxmlElement("w:fldSimple")
                toc.set(qn("w:instr"), 'TOC \\o "1-3" \\h \\z \\u')
                doc.add_paragraph()._p.append(toc)
                doc.add_paragraph("Trong Word, cập nhật trường mục lục để hiển thị số trang sau khi chỉnh theo mẫu trường.")
                doc.add_page_break()
            paragraph = doc.add_heading(title, level=min(len(prefix)-1, 3))
            if title.startswith("Chương "):
                paragraph.paragraph_format.page_break_before = True
        else:
            clean = line.replace("**", "").replace("`", "")
            doc.add_paragraph(clean[2:] if clean.startswith("- ") else clean,
                              style="List Bullet" if clean.startswith("- ") else None)
    flush_table()
    doc.save(ROOT / "docs/bao-cao-khoa-luan.docx")

    rf = summary[summary.model == "Random Forest"].iloc[0]
    slides = [
        ("Phân tích và dự đoán SOH pin", ["Nguyễn Văn Duy · 2311553949 · 23DTH2A", "GVHD theo phiếu: ThS. Vương Xuân Chí", "Bản nghiên cứu để trao đổi; chưa nghiệm thu"]),
        ("Bài toán và phạm vi", ["Ước lượng SOH sau 120 giây đầu chu kỳ xả", "SOH khác SOC và RUL", "Cell thử nghiệm; chưa có bằng chứng trên xe thực tế"]),
        ("Dữ liệu", ["Đọc MATLAB từ bản lưu công khai dẫn nguồn NASA", "2.089.048 dòng sạch; 4 pin; 636 chu kỳ xả", "2 dòng sạc thiếu tín hiệu được loại có nhật ký; không nhân bản"]),
        ("Nhãn và đặc trưng", ["SOH (%) = 100 × capacity / 2 Ah", "11 đặc trưng: chu kỳ, điện áp, dòng, nhiệt độ", "Không dùng capacity, SOH hoặc tín hiệu sau 120 giây"]),
        ("Thiết kế kiểm thử", ["Leave-one-battery-out: 4 vòng", "Huấn luyện ba pin, kiểm thử pin còn lại", "Tham số cố định; chuẩn hóa fit trên train; không tuning trên test"]),
        ("Mô hình so sánh", ["Mean baseline và Cycle Ridge", "Signal Ridge, Random Forest, HistGradientBoosting", "Demo chọn RF cố định trước khi xem điểm số"]),
        ("Kết quả thực nghiệm", [f"RF macro MAE: {rf.mae:.3f} điểm phần trăm SOH", f"RF macro RMSE: {rf.rmse:.3f}", "Không gọi MAE là độ chính xác phần trăm"]),
        ("So sánh mô hình", []),
        ("Dự đoán trên pin giữ riêng", []),
        ("Demo", ["PinLab: tổng quan, tra cứu, đánh giá, dự đoán, hồ sơ", "CSV một chu kỳ; tên cột gốc hoặc tiếng Việt", "Mẫu demo đã học, không phải test độc lập"]),
        ("Phân tích bổ sung", ["Bỏ nhóm đặc trưng: chênh lệch không đủ kết luận nhân quả", "Kiểm thử 70/30 theo thời gian: RF kém baseline SOH cuối đã biết", "Không dùng kết quả này để tuyên bố dự đoán RUL"]),
        ("Hạn chế", ["2 triệu phép đo vẫn chỉ là 4 pin và 636 mẫu SOH", "Chưa có dữ liệu Việt Nam hoặc xe vận hành thực tế", "File MAT từ bản lưu, chưa đối chiếu byte với archive S3"]),
        ("Kết luận và bước tiếp theo", ["Pipeline, dữ liệu sạch, kiểm thử, demo và tài liệu tái lập", "Bổ sung pin và điều kiện vận hành; đối chiếu kho phát hành", "Giảng viên xác nhận phạm vi và hình thức bản nộp"]),
    ]
    prs = Presentation()
    prs.slide_width, prs.slide_height = PptInches(13.333), PptInches(7.5)
    for index, (title, bullets) in enumerate(slides):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = title
        slide.shapes.title.text_frame.paragraphs[0].font.size = PptPt(32)
        frame = slide.placeholders[1].text_frame
        frame.clear()
        for j, bullet in enumerate(bullets):
            para = frame.paragraphs[0] if j == 0 else frame.add_paragraph()
            para.text = bullet
            para.font.size = PptPt(23)
        if index in (7, 8):
            image = "model_comparison.png" if index == 7 else "held_out_predictions.png"
            if index == 8:
                slide.shapes.add_picture(str(ROOT / "reports" / image), PptInches(2.8), PptInches(1.6), height=PptInches(5.4))
            else:
                slide.shapes.add_picture(str(ROOT / "reports" / image), PptInches(.6), PptInches(1.6), width=PptInches(12))
    prs.save(ROOT / "docs/slide-bao-ve.pptx")
    print(f"Đã tạo báo cáo Markdown/Word và {len(slides)} slide PowerPoint")


if __name__ == "__main__":
    main()
