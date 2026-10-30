"""Canonical text provenance across Windows/Linux and gzip CSV packaging."""
from pathlib import Path
import gzip,hashlib

def source_text(path):
    path=Path(path)
    if not path.exists() and path.suffix=='.csv':path=path.with_suffix('.csv.gz')
    raw=path.read_bytes()
    if path.suffix=='.gz':raw=gzip.decompress(raw)
    return raw.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')

def source_hash(path):
    return hashlib.sha256(source_text(path).encode('utf-8')).hexdigest()
