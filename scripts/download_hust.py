"""Tải HUST vào thư mục riêng, giữ nguyên dữ liệu NASA đang dùng."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile, is_zipfile

ROOT = Path(__file__).resolve().parents[1]
URL = (
    "https://data.mendeley.com/public-files/datasets/nsc7hnsg4s/"
    "files/5ca0ac3e-d598-4d07-8dcb-879aa047e98b/file_downloaded"
)


def inspect_archive(path):
    """Kiểm tra ZIP, không giải nén hoặc thực thi các file pickle bên trong."""
    if not is_zipfile(path):
        raise ValueError("File tải về không phải ZIP hợp lệ")
    with ZipFile(path) as archive:
        invalid = archive.testzip()
        if invalid:
            raise ValueError(f"File lỗi trong ZIP: {invalid}")
        files = [item for item in archive.infolist() if not item.is_dir()]
        cells = [item.filename for item in files if item.filename.endswith('.pkl')]
        size = sum(item.file_size for item in files)
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return {
        'source_page': 'https://data.mendeley.com/datasets/nsc7hnsg4s/2',
        'download_url': URL,
        'archive': path.name,
        'size_bytes': path.stat().st_size,
        'uncompressed_bytes': size,
        'sha256_downloaded_file': digest.hexdigest(),
        'sha256_status': 'Mã của file đã tải, chưa đối chiếu mã do tác giả công bố',
        'cell_files': cells,
        'cell_file_count': len(cells),
        'clean_row_count': None,
        'status': 'Đã kiểm tra ZIP; chưa làm sạch hoặc huấn luyện',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Kiểm tra ZIP đã tải bằng trình duyệt')
    args = parser.parse_args()
    folder = ROOT / 'data/hust'
    folder.mkdir(parents=True, exist_ok=True)
    path = args.archive or folder / 'hust_data.zip'
    if not path.exists():
        if args.archive:
            raise FileNotFoundError(path)
        temp = path.with_suffix('.zip.part')
        try:
            with urlopen(URL, timeout=120) as response, temp.open('wb') as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
            inspect_archive(temp)
            temp.replace(path)
        except Exception:
            temp.unlink(missing_ok=True)
            raise
    report = inspect_archive(path)
    (folder / 'download_audit.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
