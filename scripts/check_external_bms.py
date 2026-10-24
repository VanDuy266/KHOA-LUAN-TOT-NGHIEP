"""Kiểm tra cấu trúc và đối chiếu SOH trong file xe thực tế, không chạy mô hình SDU."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pandas as pd

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_workbook(path):
    # Đọc XML trong XLSX để không cần cài thêm thư viện Excel.
    with zipfile.ZipFile(path) as archive:
        strings = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        strings = ["".join(node.itertext()) for node in strings.findall("m:si", NS)]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in sheet.findall("m:sheetData/m:row", NS):
            values = {}
            for cell in row.findall("m:c", NS):
                column = "".join(c for c in cell.attrib["r"] if c.isalpha())
                value = cell.find("m:v", NS)
                value = value.text if value is not None else ""
                if cell.get("t") == "s":
                    value = strings[int(value)]
                values[column] = value
            rows.append(values)
    headers = rows.pop(0)
    return pd.DataFrame(rows).rename(columns=headers)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/external_bms_check.json"))
    args = parser.parse_args()
    frame = read_workbook(args.file)
    aviloo = pd.to_numeric(frame["Aviloo_SoH"], errors="coerce")
    bms = pd.to_numeric(frame["BMS_SoH"], errors="coerce")
    # Không coi mã thiếu 999999 là phần trăm sức khỏe pin.
    valid = aviloo.between(0, 120) & bms.between(0, 120)
    difference = bms[valid] - aviloo[valid]
    dates = pd.to_datetime(pd.to_numeric(frame["date_of_test"], errors="coerce"), unit="D", origin="1899-12-30")
    report = {
        "source": "https://zenodo.org/records/22643868",
        "license": "CC BY 4.0",
        "sha256": hashlib.sha256(args.file.read_bytes()).hexdigest(),
        "rows": len(frame), "columns": frame.columns.tolist(),
        "powertrain_counts": frame["typ_pohonu"].value_counts().to_dict(),
        "test_date_min": str(dates.min().date()), "test_date_max": str(dates.max().date()),
        "valid_soh_pairs_0_to_120_pct": int(valid.sum()),
        "excluded_soh_pairs": int((~valid).sum()),
        "bms_minus_aviloo_mean_pp": float(difference.mean()),
        "bms_vs_aviloo_mae_pp": float(difference.abs().mean()),
        "bms_vs_aviloo_rmse_pp": float(np.sqrt((difference ** 2).mean())),
        "compatible_with_sdu_features": False,
        "reason": "Không có chuỗi thời gian điện áp, dòng điện, nhiệt độ và chu kỳ xả để tạo 12 đặc trưng SDU.",
        "scope": "Đối chiếu hai nguồn SOH được công bố; không phải sai số mô hình SDU. Aviloo không được mặc định là phép đo dung lượng độc lập. Không suy ra RUL từ bảng này.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
