"""Tải các pin Batch-1/2 từ ZIP XJTU gốc, không cần tải cả sáu batch."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import time
import zipfile

import requests

ROOT = Path(__file__).resolve().parents[1]
RECORD = "https://zenodo.org/api/records/10963339"


class RemoteZipFile(io.RawIOBase):
    def __init__(self, url, size):
        self.url, self.size, self.position = url, size, 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        return self.position

    def read(self, size=-1):
        size = min(self.size - self.position, size if size >= 0 else self.size)
        if size <= 0:
            return b""
        for attempt in range(3):
            try:
                headers = {"Range": f"bytes={self.position}-{self.position + size - 1}"}
                with requests.get(self.url, headers=headers, stream=True, timeout=90) as response:
                    if response.status_code != 206:
                        raise ValueError(f"Máy chủ không hỗ trợ tải từng phần: HTTP {response.status_code}")
                    content = b"".join(response.iter_content(1024 * 1024))
                if len(content) != size:
                    raise ValueError("Số byte tải không khớp yêu cầu")
                self.position += size
                return content
            except (requests.RequestException, ValueError):
                if attempt == 2:
                    raise
                time.sleep(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "data/xjtu/raw")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    response = requests.get(RECORD, timeout=60)
    response.raise_for_status()
    metadata = response.json()
    source = metadata["files"][0]
    with zipfile.ZipFile(RemoteZipFile(source["links"]["self"], source["size"])) as archive:
        members = [x for x in archive.infolist() if x.filename.endswith(".mat") and
                   ("/Batch-1/" in x.filename or "/Batch-2/" in x.filename)]
    if len(members) != 23:
        raise ValueError("Danh mục nguồn không còn khớp 23 pin đã chọn")

    def download(info):
        batch = info.filename.split("/")[-2]
        target = args.output / batch / Path(info.filename).name
        target.parent.mkdir(exist_ok=True)
        # Chỉ tái dùng file có đúng CRC của thành viên ZIP nguồn.
        import zlib
        reuse = target.exists() and target.stat().st_size == info.file_size
        reuse = reuse and (zlib.crc32(target.read_bytes()) & 0xffffffff) == info.CRC
        if not reuse:
            with zipfile.ZipFile(RemoteZipFile(source["links"]["self"], source["size"])) as archive:
                content = archive.read(info.filename)  # zipfile kiểm tra CRC trước khi trả về
            temporary = target.with_suffix(".partial")
            temporary.write_bytes(content)
            temporary.replace(target)
        print(f"Đã kiểm tra/tải {batch}/{target.name}", flush=True)
        return {"member": info.filename, "path": str(target.relative_to(args.output)),
                "bytes": target.stat().st_size, "zip_crc32": f"{info.CRC:08x}",
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}

    with ThreadPoolExecutor(max_workers=2) as executor:
        files = list(executor.map(download, members))
    manifest = {"source": "https://zenodo.org/records/10963339", "doi": metadata["metadata"]["doi"],
                "license": metadata["metadata"]["license"]["id"], "source_archive_bytes": source["size"],
                "source_archive_checksum": source["checksum"], "selected_batches": [1, 2],
                "selection_reason": "Fixed full charge/discharge protocol; 1C discharge after initial 0.2C capacity test. Other batches have variable/random/partial/satellite protocols.",
                "files": files}
    (args.output.parent / "source_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Hoàn tất {len(files)} file nguyên gốc, không sửa nội dung.", flush=True)


if __name__ == "__main__":
    main()
