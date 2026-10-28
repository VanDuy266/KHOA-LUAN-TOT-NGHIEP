"""Download only the archive linked by NASA; extract four data files and README safely."""
from pathlib import Path
import hashlib,io,urllib.request,zipfile
ROOT=Path(__file__).resolve().parents[1]
URL='https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip'
EXPECTED='82302a7db4fc1b34e0b6676326610438d43b816bdf11a69d1d012a464ef2f92e'
def main():
    out=ROOT/'data/external/nasa';out.mkdir(parents=True,exist_ok=True)
    path=out/'battery_data.zip'
    if not path.exists():
        part=out/'battery_data.zip.part'
        with urllib.request.urlopen(URL,timeout=60) as source,part.open('wb') as target:
            while block:=source.read(1024*1024):target.write(block)
        with part.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        if digest!=EXPECTED:raise ValueError('NASA archive checksum changed; review before using')
        part.rename(path)
    with path.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=EXPECTED:raise ValueError('NASA archive checksum mismatch')
    with zipfile.ZipFile(path) as outer:raw=outer.read('5. Battery Data Set/1. BatteryAgingARC-FY08Q4.zip')
    names={'B0005.mat','B0006.mat','B0007.mat','B0018.mat','README.txt'}
    with zipfile.ZipFile(io.BytesIO(raw)) as inner:
        for info in inner.infolist():
            name=Path(info.filename).name
            if name in names:(out/name).write_bytes(inner.read(info))
    print('Verified NASA files:',sorted(names))
if __name__=='__main__':main()
