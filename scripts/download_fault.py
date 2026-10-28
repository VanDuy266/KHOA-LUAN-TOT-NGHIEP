"""Download only the public CC-BY Zenodo v1 dataset and extract data, never source code."""
from pathlib import Path,PurePosixPath
import urllib.request,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1]
archive=ROOT/"data/fault/raw/source.rar";archive.parent.mkdir(parents=True,exist_ok=True)
url="https://zenodo.org/api/records/18505707/files/Data%20%26%20Code.rar/content"
if not archive.exists():
    with urllib.request.urlopen(url,timeout=120) as response,archive.open("wb") as output:
        while chunk:=response.read(1024*1024):output.write(chunk)
if hashlib.md5(archive.read_bytes()).hexdigest()!="190be964af39615428834747654e853f":raise ValueError("Source checksum mismatch")
names=subprocess.check_output(["tar.exe","-tf",str(archive)],text=True).splitlines()
if not all(not PurePosixPath(n).is_absolute() and ".." not in PurePosixPath(n).parts for n in names):raise ValueError("Unsafe archive paths")
dest=ROOT/"data/fault/extracted";dest.mkdir(exist_ok=True)
subprocess.run(["tar.exe","-xf",str(archive),"-C",str(dest),"Data & Code/Data","Data & Code/Label","Data & Code/readme.txt"],check=True)
print("Public fault data checksum verified; only CSV data and README extracted.")
