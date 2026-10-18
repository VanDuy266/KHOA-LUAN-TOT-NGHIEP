"""Tải bốn file MATLAB từ bản lưu công khai và kiểm tra SHA-256."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
    target = ROOT / "data/mat"
    target.mkdir(parents=True, exist_ok=True)
    for item in manifest["files"]:
        dest = target / item["name"]
        if dest.exists():
            if hashlib.sha256(dest.read_bytes()).hexdigest() != item["sha256"]:
                raise RuntimeError(f"Checksum khác; giữ nguyên file hiện có: {dest}")
            print(f"Verified {dest.name}")
            continue
        url = item["url"]
        with urlopen(url, timeout=90) as response:
            content = response.read()
        if hashlib.sha256(content).hexdigest() != item["sha256"]:
            raise RuntimeError(f"Checksum mismatch: {dest.name}")
        temp = dest.with_suffix(".tmp")
        temp.write_bytes(content)
        temp.replace(dest)
        print(f"Downloaded and verified {dest.name}")


if __name__ == "__main__":
    main()
