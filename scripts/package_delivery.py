"""Package source, verified mirror data, artifacts and documents; exclude caches."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT.parent / "deliverables"
    destination.mkdir(exist_ok=True)
    output = destination / "KhoaLuan_NguyenVanDuy.zip"
    excluded = {".git", ".venv", ".cache", "__pycache__", ".pytest_cache", "delivery"}
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            rel = path.relative_to(ROOT)
            # Dataset đầy đủ hơn 2 triệu dòng được đóng gói riêng.
            if rel.parts[:2] in [("data", "mat"), ("data", "raw")] or path.name == "measurements_all.csv":
                continue
            if path.is_file() and not any(part in excluded for part in rel.parts) and path.suffix != ".log":
                archive.write(path, ROOT.name + "/" + str(rel))
    with zipfile.ZipFile(output) as archive:
        corrupt = archive.testzip()
        if corrupt:
            raise ValueError(f"Corrupt archive entry: {corrupt}")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    (destination / "KhoaLuan_NguyenVanDuy.sha256").write_text(digest + "  " + output.name + "\n")
    print(json.dumps({"path": str(output), "bytes": output.stat().st_size, "sha256": digest}))


if __name__ == "__main__":
    main()
