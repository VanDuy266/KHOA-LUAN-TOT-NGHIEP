"""Đóng gói sản phẩm SDU chạy sẵn, kèm manifest SHA-256; loại nguồn cũ và môi trường."""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = {
    "app",
    "src",
    "scripts",
    "tests",
    "docs",
    "reports",
    "notebooks",
    "examples",
    ".streamlit",
    "artifacts",
}
EXCLUDE = {"__pycache__", ".cache", ".pytest_cache"}
ROOT_FILES = {
    "README.md",
    "chay_windows.ps1",
    "requirements-app.txt",
    "requirements.txt",
    "requirements-deep.txt",
    "requirements.lock.txt",
    ".gitignore",
}
CLEAN_FILES = {
    "cycle_features.csv",
    "cycle_labels.csv",
    "sample_measurements.csv",
    "gru_sequences.npz",
}


def product_files():
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if not path.is_file() or any(x in EXCLUDE for x in rel.parts):
            continue
        if rel.parts[0] in INCLUDE or str(rel) in ROOT_FILES:
            if path.suffix not in {".log", ".pyc"}:
                yield path
        elif rel.parts[0] == "data":
            if len(rel.parts) == 2 and path.suffix in {".md", ".json"}:
                yield path
            elif rel.parts[1] == "xjtu" and len(rel.parts) > 2 and rel.parts[2] != "raw":
                yield path
            elif rel.parts[1] == "provenance":
                yield path
            elif rel.parts[1] == "clean" and (
                rel.parts[2] == "cells" or rel.name in CLEAN_FILES
            ):
                yield path


def main():
    destination = ROOT.parent / "deliverables"
    destination.mkdir(exist_ok=True)
    staging = destination / "VincentD_SDU"
    staging.mkdir(exist_ok=True)
    expected = {str(p.relative_to(ROOT)) for p in product_files()}
    for p in list(staging.rglob("*")):
        if p.is_file() and str(p.relative_to(staging)) not in expected:
            p.unlink()
    files = []
    for path in product_files():
        rel = path.relative_to(ROOT)
        target = staging / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        files.append(
            dict(
                path=rel.as_posix(),
                bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    manifest = dict(
        dataset="SDU", rows=10505065, cycles=20823, batteries=86, files=files
    )
    extra = ROOT / "reports/xjtu/dataset_summary.json"
    if extra.exists():
        manifest["supplementary_datasets"] = [json.loads(extra.read_text())]
    (staging / "MANIFEST_SHA256.json").write_text(json.dumps(manifest, indent=2) + "\n")
    output = destination / "VincentD_SDU.zip"
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                archive.write(
                    path, "VincentD_SDU/" + path.relative_to(staging).as_posix()
                )
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert not any(
            "/.venv/" in x or "measurements_all.csv" in x or "NASA" in x
            for x in archive.namelist()
        )
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".sha256").write_text(digest + "  " + output.name + "\n")
    print(
        json.dumps(
            dict(
                path=str(output),
                files=len(files) + 1,
                bytes=output.stat().st_size,
                sha256=digest,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
