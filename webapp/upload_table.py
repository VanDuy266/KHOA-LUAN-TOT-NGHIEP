"""Bounded CSV streaming for external uploads; never materialize the whole CSV."""
import csv,gzip,hashlib,io
import pandas as pd
from .column_mapping import read_frame
MAX_CSV_BYTES=512*1024*1024
MAX_JSON_BYTES=20*1024*1024
MAX_EXPANDED_BYTES=1024*1024*1024
MAX_SELECTED_ROWS=100000

class LimitedReader(io.RawIOBase):
    def __init__(self,source):self.source=source;self.total=0
    def readable(self):return True
    def read(self,size=-1):
        data=self.source.read(min(size if size>=0 else 262144,MAX_EXPANDED_BYTES-self.total+1))
        self.total+=len(data)
        if self.total>MAX_EXPANDED_BYTES:raise ValueError("CSV sau giải nén vượt 1 GiB; hãy tách file.")
        return data
    def readinto(self,buffer):
        data=self.read(len(buffer));buffer[:len(data)]=data;return len(data)


def _match(series,value):
    result=series.astype(str).str.strip().eq(value.strip())
    try:result |= pd.to_numeric(series,errors='coerce').eq(float(value))
    except ValueError:pass
    return result


def read_upload(upload,preview=False,needed=None,filters=None):
    if upload is None or not upload.filename:raise ValueError("Bạn chưa chọn file.")
    filename=upload.filename.lower();source=upload.stream
    source.seek(0,2);size=source.tell();source.seek(0)
    filters=filters or {}
    if any(not isinstance(k,str) or not isinstance(v,str) or not v.strip() for k,v in filters.items()):raise ValueError("Cần chọn cột lọc và nhập giá trị pin/chu kỳ.")
    if filename.endswith('.json'):
        if size>MAX_JSON_BYTES:raise ValueError("JSON tối đa 20 MiB; chuyển dữ liệu lớn sang CSV.")
        data=read_frame(source.read(),preview=False)
        scanned=len(data)
        for col,value in filters.items():
            if col not in data:raise ValueError("Cột lọc không có trong file.")
            data=data[_match(data[col],value)]
        if not preview:
            for col in data:
                if col.casefold() in {'battery','battery_id','cycle','cycle_index','phase','phase_code'} and data[col].nunique(dropna=False)>1:raise ValueError("File chứa nhiều pin/chu kỳ: chọn cột và giá trị lọc.")
        data.attrs['scanned_rows']=scanned
        return data.head(5) if preview else data
    if not filename.endswith(('.csv','.csv.gz','.gz')):raise ValueError("Chỉ nhận CSV, CSV.GZ hoặc JSON dạng bảng.")
    if size>MAX_CSV_BYTES:raise ValueError("CSV tối đa 512 MiB.")
    magic=source.read(2);source.seek(0)
    reader=gzip.GzipFile(fileobj=source) if magic==b'\x1f\x8b' else source
    prefix=reader.read(65536);reader.seek(0)
    encoding='utf-16' if prefix.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'
    line=prefix.decode(encoding,errors='replace').splitlines()[0] if prefix else ''
    try:sep=csv.Sniffer().sniff(line,delimiters=',;\t|').delimiter
    except csv.Error:sep=','
    options=dict(encoding=encoding,sep=sep,decimal=',' if sep==';' else '.')
    columns=pd.read_csv(LimitedReader(reader),nrows=0,**options).columns.tolist()
    if len(columns)>128:raise ValueError("Tối đa 128 cột; chỉ xuất những tín hiệu cần phân tích.")
    if not set(filters)<=set(columns):raise ValueError("Cột lọc không có trong file.")
    reader.seek(0)
    if preview:return pd.read_csv(LimitedReader(reader),nrows=5,**options)
    if needed is not None and not set(needed)<=set(columns):raise ValueError("Cột tín hiệu hoặc SOC không có trong file.")
    group_columns=[c for c in columns if c.casefold() in {'battery','battery_id','cycle','cycle_index','phase','phase_code'}]
    keep=None if needed is None else list(set(needed)|set(filters)|set(group_columns))
    parts=[];selected=0;scanned=0;seen={c:set() for c in group_columns}
    chunks=pd.read_csv(LimitedReader(reader),usecols=keep,chunksize=50000,**options)
    try:
        for chunk in chunks:
            scanned+=len(chunk)
            if scanned>10000000:raise ValueError("Tối đa 10 triệu dòng quét; hãy tách dữ liệu theo pin/chu kỳ.")
            for col,value in filters.items():chunk=chunk[_match(chunk[col],value)]
            for col in group_columns:
                seen[col].update(chunk[col].astype(str).unique())
                if len(seen[col])>1:raise ValueError("File chứa nhiều pin/chu kỳ: chọn cột và giá trị lọc trước khi phân tích.")
            selected+=len(chunk)
            if selected>MAX_SELECTED_ROWS:raise ValueError("Đoạn đã chọn vượt 100.000 dòng; lọc một pin và một chu kỳ hoặc tách đoạn đo.")
            if len(chunk):parts.append(chunk)
    finally:chunks.close()
    if not parts:raise ValueError("Không có dòng khớp pin/chu kỳ đã chọn.")
    result=pd.concat(parts,ignore_index=True);result.attrs['scanned_rows']=scanned
    return result


def upload_sha256(upload):
    upload.stream.seek(0);digest=hashlib.sha256()
    while part:=upload.stream.read(1024*1024):digest.update(part)
    upload.stream.seek(0);return digest.hexdigest()


def carry_context(out,source,chosen):
    aliases={'battery':{'battery','battery_id'},'cycle':{'cycle','cycle_index'},'phase':{'phase','phase_code'}}
    for key,names in aliases.items():
        column=chosen.get(key) or next((c for c in source if c.casefold() in names),'')
        if not column or column not in source:continue
        values=source[column]
        if values.nunique(dropna=False)!=1:raise ValueError("Nhóm đã chọn còn nhiều mã pin, chu kỳ hoặc giai đoạn.")
        if key=='battery':out['battery']=values.astype(str).str.strip().to_numpy()
        elif key=='cycle':
            numeric=pd.to_numeric(values,errors='coerce')
            if numeric.notna().all() and (numeric>0).all() and (numeric%1==0).all():out['cycle']=numeric.astype(int).to_numpy()
        else:
            codes=values.replace({'primary':0,'second_life':1})
            numeric=pd.to_numeric(codes,errors='coerce')
            if numeric.isin([0,1]).all():out['phase_code']=numeric.astype(int).to_numpy()
    return out
