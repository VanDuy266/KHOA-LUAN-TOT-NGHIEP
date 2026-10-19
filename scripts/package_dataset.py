"""Đóng gói bộ nguồn SDU đã chọn, không sửa hoặc giải nén lại CSV gzip."""

import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = Path((ROOT / "data/source/location.txt").read_text().strip())
    assert (source / "source_rows").exists() and (
        source / "verification/summary.json"
    ).exists()
    output = ROOT.parent / "deliverables/Dataset_SDU_10tr_dong.zip"
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, path.relative_to(source))
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
    output.with_suffix(".sha256").write_text(
        hashlib.sha256(output.read_bytes()).hexdigest() + "  " + output.name + "\n"
    )
    print(output)


if __name__ == "__main__":
    main()
