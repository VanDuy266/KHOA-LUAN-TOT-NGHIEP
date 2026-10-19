"""Sinh báo cáo và slide từ bảng kết quả SDU; không điền số liệu thủ công."""

import json
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from pptx import Presentation
from pptx.util import Inches, Pt as PptPt
from pptx.dml.color import RGBColor

ROOT = Path(__file__).resolve().parents[1]


def md_table(frame):
    def fmt(x):
        return f"{x:.3f}" if isinstance(x, float) else str(x)

    return "\n".join(
        [
            "| " + " | ".join(map(str, frame.columns)) + " |",
            "| " + " | ".join(["---"] * len(frame.columns)) + " |",
        ]
        + [
            "| " + " | ".join(fmt(x) for x in row) + " |"
            for row in frame.itertuples(index=False, name=None)
        ]
    )


def figures(data, predictions):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
    for ax, (phase, part) in zip(axes, data.groupby("phase")):
        for _, group in part.groupby("battery"):
            group = group.sort_values("cycle")
            ax.plot(group.cycle, group.soh_pct, alpha=0.25, linewidth=0.7)
        ax.set(
            title={"primary": "Sử dụng ban đầu", "second_life": "Tái sử dụng"}[phase],
            xlabel="Chu kỳ",
            ylabel="SOH (%)",
        )
    fig.tight_layout()
    fig.savefig(ROOT / "reports/soh_by_phase.png", dpi=180)
    plt.close(fig)
    rf = predictions[predictions.model == "Random Forest"]
    fig, ax = plt.subplots(figsize=(9, 4))
    for phase, part in rf.groupby("phase"):
        ax.scatter(
            part.actual_soh,
            part.predicted_soh - part.actual_soh,
            s=3,
            alpha=0.25,
            label=phase,
        )
    ax.axhline(0, color="black", linewidth=0.7)
    ax.set(xlabel="SOH thực tế (%)", ylabel="Sai số (điểm % SOH)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(ROOT / "reports/error_analysis.png", dpi=180)
    plt.close(fig)
    importance = pd.read_csv(ROOT / "reports/feature_importance.csv").sort_values(
        "importance"
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(importance.feature, importance.importance, color="#087f70")
    ax.set(xlabel="Mức quan trọng theo cây")
    fig.tight_layout()
    fig.savefig(ROOT / "reports/feature_importance.png", dpi=180)
    plt.close(fig)


def word_report(text):
    doc = Document()
    doc.core_properties.author = "Nguyễn Văn Duy"
    doc.core_properties.title = (
        "Phân tích và dự đoán tình trạng sức khỏe pin xe điện bằng các mô hình học máy"
    )
    for name in ["Normal", "Title", "Heading 1", "Heading 2", "Heading 3"]:
        doc.styles[name].font.name = "Times New Roman"
        doc.styles[name].font.color.rgb = __import__("docx").shared.RGBColor(0, 0, 0)
    normal = doc.styles["Normal"]
    normal.font.size = Pt(13)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(6)
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(3.5)
    section.right_margin = Cm(2)
    section.top_margin = section.bottom_margin = Cm(2.5)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)
    body = False
    table_lines = []

    def flush():
        if not table_lines:
            return
        rows = [[c.strip() for c in line.strip("|").split("|")] for line in table_lines]
        rows = [x for x in rows if not all(re.fullmatch(":?-+:?", c) for c in x)]
        table = doc.add_table(rows=0, cols=len(rows[0]))
        table.style = "Table Grid"
        for index, row in enumerate(rows):
            cells = table.add_row().cells
            for cell, value in zip(cells, row):
                cell.text = value
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.line_spacing = 1.1
                    for run in paragraph.runs:
                        run.font.size = Pt(9)
                        run.bold = index == 0
            if index == 0:
                mark = OxmlElement("w:tblHeader")
                table.rows[0]._tr.get_or_add_trPr().append(mark)
        table_lines.clear()

    for line in text.splitlines():
        if line.startswith("|"):
            table_lines.append(line)
            continue
        flush()
        if not line.strip():
            continue
        if line == "# Tóm tắt":
            body = True
            doc.add_page_break()
            doc.add_heading("Mục lục", level=1)
            # Mục lục tĩnh theo đề mục để luôn hiển thị cả khi chưa cập nhật trường Word.
            page_file = ROOT / "reports/document_pages.json"
            pages = json.loads(page_file.read_text()) if page_file.exists() else {}
            titles = re.findall(r"^# (.+)$", text, re.M)[2:]
            for title in titles:
                if title not in ["KHÓA LUẬN TỐT NGHIỆP"]:
                    doc.add_paragraph(
                        title + ("  ·  " + str(pages[title]) if title in pages else "")
                    )
            doc.add_page_break()
        if not body:
            paragraph = doc.add_paragraph(line.lstrip("# "))
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.bold = line.startswith("#")
                run.font.size = Pt(16 if line.startswith("#") else 13)
            continue
        image = re.fullmatch(r"!\[(.*?)\]\((.*?)\)", line)
        if image:
            doc.add_picture(
                str((ROOT / "docs" / image.group(2)).resolve()), width=Cm(15.3)
            )
            paragraph = doc.add_paragraph(image.group(1))
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif line.startswith("#"):
            prefix, title = line.split(" ", 1)
            paragraph = doc.add_heading(title, level=min(len(prefix), 3))
            if len(prefix) == 1:
                paragraph.paragraph_format.page_break_before = True
        else:
            doc.add_paragraph(line.replace("**", "").replace("`", ""))
    flush()
    doc.save(ROOT / "docs/bao-cao-khoa-luan.docx")


def slides(summary, temporal):
    rf = summary[summary.model == "Random Forest"].iloc[0]
    sections = [
        (
            "Phân tích và dự đoán\nsức khỏe pin xe điện",
            [
                "Nguyễn Văn Duy · 2311553949 · 23DTH2A",
                "Chuyên ngành Khoa Học Dữ Liệu",
                "GVHD: ThS. Vương Xuân Chí",
            ],
            None,
        ),
        (
            "Bài toán nghiên cứu",
            [
                "Quan sát 120 giây đầu xả → ước lượng SOH",
                "SOH = dung lượng xả / 2,4 Ah × 100",
                "Thực nghiệm cấp tế bào trong phòng thí nghiệm",
            ],
            None,
        ),
        (
            "Nguồn dữ liệu SDU 2025",
            [
                "Wang, Gao và Tian · Đại học Sơn Đông",
                "Zenodo DOI: 10.5281/zenodo.14859405 · CC BY 4.0",
                "86 pin NMC(532)/graphite qua hai giai đoạn",
            ],
            None,
        ),
        (
            "Từ nguồn đến dữ liệu mô hình",
            [
                "145.112.317 dòng nguồn → 30.929.675 dòng xả tham chiếu",
                "Bản chọn: 10.000.000 dòng, đủ 20.823 chu kỳ",
                "Giữ nguyên cửa sổ đầu xả; lấy thưa đoạn sau",
            ],
            None,
        ),
        ("SOH theo hai giai đoạn", [], "reports/soh_by_phase.png"),
        (
            "Chất lượng và truy xuất nguồn",
            [
                "Đối chiếu MD5 gói gốc và SHA-256 file được chọn",
                "Không thiếu tín hiệu bắt buộc, không trùng khóa thời gian",
                "25 điểm nghi vấn được giữ; không nằm trong 120 giây đầu",
            ],
            None,
        ),
        (
            "Đặc trưng và nhãn",
            [
                "12 đặc trưng: chu kỳ, giai đoạn, thống kê V/I/T",
                "Không dùng dung lượng, nhãn hoặc tín hiệu cuối chu kỳ",
                "GRU: 25 vị trí × 3 tín hiệu + ngữ cảnh chu kỳ/giai đoạn",
            ],
            None,
        ),
        (
            "Bốn mô hình và mốc đối chứng",
            [
                "Ridge: tuyến tính, điều chuẩn L2",
                "Random Forest và LightGBM: quan hệ phi tuyến trên bảng",
                "GRU: học chuỗi đầu xả; thêm mốc dự đoán trung bình",
            ],
            None,
        ),
        (
            "Thiết kế kiểm thử",
            [
                "GroupKFold 5 vòng, chia theo 86 pin vật lý",
                "Hai giai đoạn của một pin luôn ở cùng phía",
                "Chuẩn hóa chỉ học trên train; cấu hình và seed cố định",
            ],
            None,
        ),
        ("So sánh sai số", [], "reports/model_comparison.png"),
        (
            "Kết quả Random Forest",
            [
                f"MAE: {rf.mae:.3f} điểm phần trăm SOH",
                f"RMSE: {rf.rmse:.3f} · R²: {rf.r2:.3f}",
                "Chỉ số là trung bình theo pin giữ riêng",
            ],
            None,
        ),
        ("Thực tế và dự đoán", [], "reports/held_out_predictions.png"),
        ("Sai số và giới hạn", [], "reports/error_analysis.png"),
        (
            "Kiểm tra bổ sung",
            [
                "Bỏ số chu kỳ, bỏ giai đoạn, chỉ dùng điện áp",
                "Kiểm thử riêng 70/30 theo thời gian trong từng pin/giai đoạn",
                *[f"{row.model}: MAE {row.mae:.3f}" for row in temporal.itertuples()],
            ],
            None,
        ),
        (
            "Sản phẩm Vincent D",
            [
                "Tra cứu hai giai đoạn, tín hiệu và so sánh chu kỳ",
                "Dự đoán một/lô, lịch sử và phiếu kết quả",
                "Chất lượng, nguồn dữ liệu và bảng thực nghiệm",
            ],
            None,
        ),
        ("Giao diện ứng dụng", [], "docs/images/vincent_d_sdu_overview.png"),
        (
            "Kết luận và hướng phát triển",
            [
                "Hoàn thành quy trình dữ liệu → mô hình → ứng dụng",
                "Chưa kiểm chứng trên bộ pin xe thực tế tại Việt Nam",
                "Mở rộng điều kiện vận hành, đánh giá độc lập và độ bất định",
            ],
            None,
        ),
        (
            "Tài liệu và sản phẩm bàn giao",
            [
                "Mã nguồn, mô hình, bảng đặc trưng và dữ liệu nguồn",
                "Notebook đã chạy, CSV thực nghiệm và biểu đồ",
                "Báo cáo Word/PDF, slide và hồ sơ trích dẫn",
            ],
            None,
        ),
    ]
    prs = Presentation()
    prs.core_properties.author = "Nguyễn Văn Duy"
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    for i, (title, bullets, image) in enumerate(sections):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor.from_string("F6F8F3")
        bar = slide.shapes.add_shape(1, 0, 0, Inches(0.16), prs.slide_height)
        bar.fill.solid()
        bar.fill.fore_color.rgb = RGBColor.from_string("087F70")
        bar.line.fill.background()

        def text_box(x, y, w, h, text, size=24, color="193431", bold=False):
            box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
            box.text_frame.word_wrap = True
            for j, line in enumerate(text.split("\n")):
                p = (
                    box.text_frame.paragraphs[0]
                    if j == 0
                    else box.text_frame.add_paragraph()
                )
                p.text = line
                p.font.name = "Arial"
                p.font.size = PptPt(size)
                p.font.bold = bold
                p.font.color.rgb = RGBColor.from_string(color)
                p.space_after = PptPt(16)
            return box

        text_box(
            0.65,
            0.3,
            12,
            0.4,
            "VINCENT D / NGHIÊN CỨU SỨC KHỎE PIN",
            12,
            "087F70",
            True,
        )
        text_box(0.65, 0.95, 12, 1.3, title, 32, bold=True)
        if image and (ROOT / image).exists():
            from PIL import Image

            path = ROOT / image
            with Image.open(path) as img:
                ratio = img.width / img.height
            width = min(11.8, 4.5 * ratio)
            height = width / ratio
            slide.shapes.add_picture(
                str(path),
                Inches((13.333 - width) / 2),
                Inches(2),
                width=Inches(width),
                height=Inches(height),
            )
        else:
            text_box(0.85, 2.5, 11.8, 3.7, "\n".join("• " + x for x in bullets), 24)
        text_box(
            0.65,
            7.05,
            11,
            0.25,
            "Nguyễn Văn Duy · MSSV 2311553949 · Khoa Học Dữ Liệu",
            10,
            "60766D",
        )
        text_box(12, 7.0, 0.6, 0.3, f"{i+1:02d}", 12, "087F70")
    prs.save(ROOT / "docs/slide-bao-ve.pptx")


def main():
    data = pd.read_csv(ROOT / "reports/features.csv")
    pred = pd.read_csv(ROOT / "reports/predictions.csv")
    summary = pd.read_csv(ROOT / "reports/metrics_summary.csv")
    metrics = pd.read_csv(ROOT / "reports/metrics_by_battery.csv")
    phase = pd.read_csv(ROOT / "reports/metrics_by_phase.csv")
    ablation = pd.read_csv(ROOT / "reports/ablation_summary.csv")
    temporal = (
        pd.read_csv(ROOT / "reports/temporal_metrics.csv")
        .groupby("model")[["mae", "rmse"]]
        .mean()
        .reset_index()
    )
    timing = (
        pd.read_csv(ROOT / "reports/timings.csv")
        .groupby("model")[["fit_seconds", "predict_seconds"]]
        .mean()
        .reset_index()
        .fillna("Không đo riêng")
    )
    rf = summary[summary.model == "Random Forest"].iloc[0]
    best = summary.sort_values("mae").iloc[0]
    figures(data, pred)
    from sys import path

    path.insert(0, str(ROOT / "app"))
    path.insert(0, str(ROOT / "src"))
    from labels import vietnamese_table, COLUMNS
    from battery_soh.features import FEATURES

    codes = pd.DataFrame(
        [
            ("scripts/download_data.py", "Nhận bộ chọn từ nhánh dữ liệu hoặc ZIP"),
            ("scripts/prepare_data.py", "Đối chiếu SHA, tạo Parquet và kiểm đặc trưng"),
            ("src/battery_soh/features.py", "Tính đúng 12 đặc trưng, kiểm nhãn"),
            ("scripts/run_experiment.py", "Kiểm thử các mô hình bảng theo pin"),
            ("scripts/train_gru.py", "Tạo chuỗi, chuẩn hóa theo train và kiểm thử GRU"),
            ("scripts/analyze_results.py", "Bỏ đặc trưng và kiểm thử thời gian"),
            ("scripts/check_dataset.py", "Quét toàn bộ Parquet, kiểm khóa và nhãn"),
            ("app/prediction.py", "Đọc CSV và dự đoán một/lô"),
            ("app/app_data.py", "Đọc chu kỳ cần xem và nạp mô hình"),
            ("app/screens/", "Các màn hình chức năng"),
            ("scripts/build_notebook.py", "Sinh và thực thi notebook"),
            ("scripts/build_documents.py", "Sinh báo cáo và slide từ kết quả"),
        ],
        columns=["File", "Chức năng"],
    )
    replacements = {
        "RF_MAE": f"{rf.mae:.3f}",
        "RF_RMSE": f"{rf.rmse:.3f}",
        "RF_R2": f"{rf.r2:.3f}",
        "FEATURE_TABLE": md_table(
            pd.DataFrame(
                {"Tên cột": FEATURES, "Ý nghĩa": [COLUMNS[x] for x in FEATURES]}
            )
        ),
        "SUMMARY_TABLE": md_table(vietnamese_table(summary)),
        "PHASE_TABLE": md_table(
            vietnamese_table(
                data.groupby("phase")
                .agg(
                    pins=("battery", "nunique"),
                    cycles=("cycle", "size"),
                    soh_min=("soh_pct", "min"),
                    soh_max=("soh_pct", "max"),
                )
                .reset_index()
            )
        ),
        "PHASE_METRICS_TABLE": md_table(vietnamese_table(phase)),
        "BY_BATTERY_TABLE": md_table(
            vietnamese_table(
                metrics[metrics.model == "Random Forest"][
                    ["held_out_battery", "fold", "n_test", "mae", "rmse", "r2"]
                ]
            )
        ),
        "ABLATION_TABLE": md_table(vietnamese_table(ablation)),
        "TEMPORAL_TABLE": md_table(vietnamese_table(temporal)),
        "TIMING_TABLE": md_table(vietnamese_table(timing)),
        "CODE_TABLE": md_table(codes),
        "PARAMETER_TABLE": md_table(
            pd.DataFrame(
                {
                    "Mô hình": ["Mốc trung bình", "Ridge", "Random Forest", "LightGBM"],
                    "Cấu hình": [
                        "Trung bình SOH train",
                        "StandardScaler + alpha 10",
                        "100 cây; sâu 16; lá ≥5; mẫu 0,7; 2 luồng",
                        "150 cây; 15 lá; học 0,05; L2=1; 2 luồng",
                    ],
                }
            )
        ),
        "RESULT_DISCUSSION": f'Trong các cấu hình đã chạy, {best.model} có MAE trung bình thấp nhất ({best.mae:.3f}). Random Forest giảm MAE {100*(1-rf.mae/summary.loc[summary.model=="Ridge","mae"].iloc[0]):.1f}% so với Ridge. GRU đạt MAE {summary.loc[summary.model=="GRU","mae"].iloc[0]:.3f}; mạng chuỗi phức tạp hơn không tự đảm bảo sai số thấp hơn trên bộ chọn này.',
        "ERROR_DISCUSSION": "Các pin có MAE Random Forest cao nhất trong lần chạy: "
        + "; ".join(
            f"{row.held_out_battery}: {row.mae:.3f}"
            for row in metrics[metrics.model == "Random Forest"]
            .nlargest(5, "mae")
            .itertuples()
        )
        + " điểm phần trăm SOH. Cần thận trọng khi diễn giải một chỉ số chung cho mọi pin.",
        "ABLATION_DISCUSSION": "MAE đủ đặc trưng là "
        + f"{rf.mae:.3f}"
        + ". Các cấu hình bỏ nhóm cho kết quả: "
        + "; ".join(
            f"{row.configuration}: {row.mae:.3f}"
            for row in ablation[ablation.configuration != "Full features"].itertuples()
        )
        + ".",
        "TEMPORAL_DISCUSSION": "MAE trung bình giữa các cặp pin/giai đoạn: "
        + "; ".join(f"{row.model}: {row.mae:.3f}" for row in temporal.itertuples())
        + " điểm phần trăm SOH. Đây là kết quả riêng của thiết kế thời gian.",
    }
    xml = ROOT / "reports/pytest-results.xml"
    if xml.exists():
        suite = ET.parse(xml).getroot().find("testsuite")
        replacements["TEST_DISCUSSION"] = (
            f'Lần kiểm thử lưu trong reports/pytest-results.xml gồm {suite.get("tests")} trường hợp, {suite.get("failures")} thất bại, {suite.get("errors")} lỗi và {suite.get("skipped")} bỏ qua. Tệp dataset_check.json ghi kết quả kiểm tra toàn bộ 10 triệu dòng.'
        )
    else:
        raise ValueError("Chưa có kết quả kiểm thử")
    text = (ROOT / "docs/bao-cao-template.md").read_text()
    for key, value in replacements.items():
        text = text.replace("{{" + key + "}}", value)
    if "{{" in text:
        raise ValueError("Còn biến mẫu báo cáo")
    # Ảnh lấy từ ứng dụng thật, không dựng lại giao diện trong báo cáo.
    if (ROOT / "docs/images/vincent_d_sdu_overview.png").exists():
        text = text.replace(
            "## 5.3. Mô hình ứng dụng",
            "![Hình 5.1. Tổng quan Vincent D với dữ liệu SDU](images/vincent_d_sdu_overview.png)\n\n## 5.3. Mô hình ứng dụng",
        )
    (ROOT / "docs/bao-cao-khoa-luan.md").write_text(text)
    word_report(text)
    slides(summary, temporal)
    # PDF là bước tùy chọn khi máy có LibreOffice và pdftotext.
    office = shutil.which("soffice")
    pdf = ROOT / "docs/bao-cao-khoa-luan.pdf"
    if office:
        for iteration in range(2):
            subprocess.run(
                [
                    office,
                    "-env:UserInstallation=file://"
                    + str(Path(tempfile.gettempdir()) / "lo-vincent-final"),
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(ROOT / "docs"),
                    str(ROOT / "docs/bao-cao-khoa-luan.docx"),
                ],
                check=True,
            )
            converter = shutil.which("pdftotext")
            if converter:
                output = subprocess.check_output(
                    [converter, "-layout", str(pdf), "-"], text=True
                )
                pages = {}
                for index, page in enumerate(output.split("\f"), 1):
                    if index < 3:
                        continue
                    normalized = " ".join(page.split())
                    for title in re.findall(r"^# (.+)$", text, re.M)[2:]:
                        if normalized.startswith(title):
                            pages[title] = index
                (ROOT / "reports/document_pages.json").write_text(
                    json.dumps(pages, ensure_ascii=False, indent=2) + "\n"
                )
                word_report(text)
        print("Đã xuất PDF và đối chiếu số trang mục lục.")
    elif pdf.exists():
        pdf.unlink()
        print("Chưa xuất PDF mới: máy không có LibreOffice; bản Word đã cập nhật.")
    print("Đã tạo báo cáo Word/Markdown và 18 slide từ kết quả SDU.")


if __name__ == "__main__":
    main()
