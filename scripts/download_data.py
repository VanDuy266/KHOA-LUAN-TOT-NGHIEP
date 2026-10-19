"""Nhận ZIP SDU đã tải hoặc tải nhánh dataset bằng Git đã đăng nhập."""

import argparse
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path)
    args = parser.parse_args()
    folder = ROOT / "data/source"
    folder.mkdir(exist_ok=True)
    if args.zip:
        target = folder / "dataset"
        target.mkdir(exist_ok=True)
        with zipfile.ZipFile(args.zip) as archive:
            for info in archive.infolist():
                path = target / info.filename
                if not path.resolve().is_relative_to(target.resolve()):
                    raise ValueError("Đường dẫn ZIP không hợp lệ")
            archive.extractall(target)
        matches = list(target.rglob("dataset_summary.json"))
        location = next(
            (p.parent for p in matches if (p.parent / "source_rows").exists()), None
        )
        if location is None:
            raise ValueError("ZIP không chứa bộ SDU 10 triệu dòng")
    elif (folder / "location.txt").exists():
        location = Path((folder / "location.txt").read_text().strip())
        if not (location / "source_rows").exists():
            raise FileNotFoundError(
                "Đường dẫn dữ liệu không còn tồn tại; nhập lại --zip"
            )
    else:
        location = folder / "dataset"
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--single-branch",
                "--branch",
                "dataset-sdu-10tr",
                "https://github.com/VanDuy266/KHOA-LUAN-TOT-NGHIEP.git",
                str(location),
            ],
            check=True,
        )
    (folder / "location.txt").write_text(str(location.resolve()))
    print("Nguồn SDU:", location)


if __name__ == "__main__":
    main()
