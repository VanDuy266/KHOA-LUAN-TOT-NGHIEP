"""Tải dữ liệu gốc SDU 2025 và đối chiếu mã MD5 từ Zenodo."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen

FOLDER=Path(__file__).resolve().parent
CHUNK=8*1024*1024


def digest(path):
    checksum=hashlib.md5()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''):
            checksum.update(block)
    return 'md5:'+checksum.hexdigest()


def part(source,index):
    folder=FOLDER/(source['key']+'.parts')
    folder.mkdir(exist_ok=True)
    start=index*CHUNK
    end=min(source['size'],start+CHUNK)-1
    path=folder/str(index)
    if path.exists() and path.stat().st_size==end-start+1:return
    for attempt in range(4):
        try:
            request=Request(source['links']['self'],headers={'Range':f'bytes={start}-{end}'})
            temporary=path.with_suffix('.tmp')
            with urlopen(request,timeout=90) as response,temporary.open('wb') as output:
                if response.status!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{end}/{source["size"]}':
                    raise ValueError('Máy chủ trả về sai phần dữ liệu')
                while block:=response.read(1024*1024):output.write(block)
            if temporary.stat().st_size!=end-start+1:raise ValueError('Phần tải chưa đủ')
            temporary.replace(path)
            return
        except Exception:
            if attempt==3:raise


def main():
    record=json.loads((FOLDER/'zenodo_record.json').read_text())
    sources=record['files']
    jobs=[]
    for source in sources:
        path=FOLDER/source['key']
        if path.exists():
            if digest(path)!=source['checksum']:raise ValueError('File hiện có không khớp MD5')
            print('Đã kiểm tra',source['key'],flush=True)
            continue
        jobs.extend((source,index) for index in range((source['size']+CHUNK-1)//CHUNK))
    with ThreadPoolExecutor(max_workers=16) as pool:
        tasks=[pool.submit(part,source,index) for source,index in jobs]
        for done,future in enumerate(as_completed(tasks),1):
            future.result()
            if done%16==0:print(f'Đã tải {done}/{len(tasks)} phần',flush=True)
    checks=[]
    for source in sources:
        path=FOLDER/source['key']
        if not path.exists():
            temp=path.with_suffix('.verified.part')
            count=(source['size']+CHUNK-1)//CHUNK
            folder=FOLDER/(source['key']+'.parts')
            with temp.open('wb') as output:
                for index in range(count):output.write((folder/str(index)).read_bytes())
            if temp.stat().st_size!=source['size'] or digest(temp)!=source['checksum']:
                raise ValueError('File không khớp MD5 Zenodo: '+source['key'])
            temp.replace(path)
            for item in folder.iterdir():item.unlink()
            folder.rmdir()
        checks.append(dict(file=path.name,size_bytes=path.stat().st_size,md5=source['checksum'],verified=True))
        print('VERIFIED',checks[-1],flush=True)
    (FOLDER/'download_verified.json').write_text(json.dumps(dict(doi=record['doi'],files=checks),indent=2))


if __name__=='__main__':main()
