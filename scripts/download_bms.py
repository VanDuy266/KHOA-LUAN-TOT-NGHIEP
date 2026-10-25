"""Download immutable BMS archives recorded in the source manifest; verify SHA256."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'data/bms/provenance/source_manifest.json').read_text(encoding='utf-8'))
for entry in manifest['files']:
    path=ROOT/entry['file'];path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists(): subprocess.run(['curl.exe','-L','--fail',entry['url'],'-o',str(path)],check=True)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']: raise ValueError(f'Hash mismatch: {path}')
    print('Verified',entry['vehicle'])
