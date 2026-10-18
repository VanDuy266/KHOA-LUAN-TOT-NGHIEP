"""Tạo gói dataset sạch riêng, kèm thống kê và nguồn, không nhân bản dữ liệu."""
import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT.parent / "deliverables"
    destination.mkdir(exist_ok=True)
    output = destination / "Dataset_Pin_NASA_2tr_dong.zip"
    files = ["data/clean/measurements_all.csv", "data/clean/measurements.csv", "data/clean/cycle_features.csv",
        "data/README.md", "data/manifest.json", "data/mat/README.txt", "reports/dataset_summary.json",
        "reports/dataset_check.json", "reports/data_audit.csv", "reports/removed_measurements.csv",
        "scripts/download_data.py", "scripts/prepare_data.py", "scripts/check_dataset.py",
        "src/battery_soh/features.py", "requirements-app.txt"]
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(ROOT / name, name)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("Gói ZIP bị lỗi")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".sha256").write_text(digest + "  " + output.name + "\n")
    print(f"Dataset ZIP: {output} ({output.stat().st_size / 1024**2:.1f} MiB)")


if __name__ == "__main__":
    main()
