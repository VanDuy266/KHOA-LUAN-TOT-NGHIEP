"""Chép nguyên văn dòng được chọn từ CSV nguồn; không đổi giá trị/tên cột/thứ tự."""
import gzip
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

OUT=Path(__file__).resolve().parent
BASE=OUT.parent
DEST=OUT/'source_rows'


def preserve_one(record):
    row=type("Record",(),record)()
    phase=row.phase
    name="Primary_use_phase.zip" if phase=="primary" else "Second_life_phase.zip"
    folder=DEST/Path(name).stem
    folder.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(BASE/name) as archive:
        selection=OUT/'measurements'/f'{phase}_pin_{row.battery:02d}.csv.gz'
        indexes=pd.read_csv(selection,usecols=['source_row']).source_row.to_numpy(dtype=np.int64)
        if len(indexes)!=row.selected_discharge_rows or len(np.unique(indexes))!=len(indexes):
            raise ValueError('Số dòng chọn không khớp nhật ký')
        mask=np.zeros(row.source_rows,dtype=bool)
        mask[indexes]=True
        output=folder/(row.source_file+'.gz')
        temp=output.with_suffix('.tmp')
        selected_hash=hashlib.sha256();count=0;original_rows=0
        # ZIP chứa CSV số liệu dạng một bản ghi trên một dòng; kiểm tra số dòng.
        with archive.open(row.source_file) as source,gzip.open(temp,'wb',compresslevel=1) as target:
            header=source.readline()
            target.write(header);selected_hash.update(header)
            for line in source:
                if not line.strip():continue
                if original_rows>=len(mask):raise ValueError('CSV nguồn có thêm bản ghi ngoài nhật ký')
                if mask[original_rows]:
                    target.write(line);selected_hash.update(line);count+=1
                original_rows+=1
        if original_rows!=row.source_rows or count!=row.selected_discharge_rows:
            raise ValueError('Không khớp số bản ghi CSV gốc và bản chọn')
        temp.replace(output)
        digest=hashlib.sha256()
        with gzip.open(output,'rb') as verify:
            for block in iter(lambda:verify.read(1024*1024),b''):digest.update(block)
        if digest.hexdigest()!=selected_hash.hexdigest():
            raise ValueError('Nội dung CSV xuất không giống nguyên văn dòng nguồn')
    return dict(phase=phase,battery=row.battery,source_archive=name,source_file=row.source_file,source_rows=row.source_rows,selected_rows=count,output=str(output.relative_to(OUT)),uncompressed_csv_sha256=digest.hexdigest(),source_row_bytes_preserved=True,source_header_preserved=True,source_order_preserved=True)

def main():
    from concurrent.futures import ProcessPoolExecutor, as_completed
    audit=pd.read_csv(OUT/'audit_by_file.csv')
    records=audit.loc[audit.selected_cycles>0].to_dict('records')
    manifest=[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(preserve_one,record) for record in records]
        for future in as_completed(futures):
            result=future.result()
            manifest.append(result)
            pd.DataFrame(manifest).sort_values(['phase','battery']).to_csv(OUT/'source_preservation_audit.csv',index=False)
            print(f"Giữ nguyên văn {len(manifest)}/{len(records)} file · {result['selected_rows']:,} dòng",flush=True)
    summary=dict(files=len(manifest),selected_rows=sum(x['selected_rows'] for x in manifest),
        every_source_row_preserved_verbatim=True,source_headers_preserved=True,
        source_order_preserved=True,source_archives_unchanged=True,
        method='Copy original CSV header and selected data lines as bytes; verify SHA-256 of decompressed output against copied source bytes. No numeric reformatting, interpolation, imputation or renumbering.')
    (OUT/'source_preservation_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
