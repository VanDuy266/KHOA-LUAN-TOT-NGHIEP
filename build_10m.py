"""Giữ đủ chu kỳ, giữ mọi mẫu 120 giây đầu, giảm điểm đo ở đoạn sau.

Chỉ chọn dòng nguyên văn; không nội suy, sửa số đo hoặc tự xóa nghi vấn nhiễu.
"""
import csv
import gzip
import hashlib
import json
import shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import zipfile
import numpy as np
import pandas as pd

OUT=Path(__file__).resolve().parent
BASE=OUT.parent
FULL=BASE/'selection'
TARGET=10_000_000


def scan(record):
    frame=pd.read_csv(FULL/record['output'],usecols=['Cycle_Index','Test_Time(s)'])
    group=frame.groupby('Cycle_Index')['Test_Time(s)']
    first=group.transform('min');last=group.transform('max')
    mandatory=(frame['Test_Time(s)']<=first+120)|(frame['Test_Time(s)']==last)
    info=frame.assign(mandatory=mandatory).groupby('Cycle_Index').agg(rows=('Cycle_Index','size'),mandatory=('mandatory','sum')).reset_index().rename(columns={'Cycle_Index':'cycle'})
    info['phase']=record['phase'];info['battery']=record['battery']
    return info


def copy(record,budgets):
    frame=pd.read_csv(FULL/record['output'],usecols=['Cycle_Index','Test_Time(s)'])
    keep=np.zeros(len(frame),dtype=bool)
    for cycle,part in frame.groupby('Cycle_Index',sort=False):
        part=part.sort_values('Test_Time(s)',kind='stable')
        t=part['Test_Time(s)'].to_numpy()
        mandatory=(t<=t[0]+120)|(t==t[-1])
        count=int(budgets[int(cycle)])
        optional=part.index.to_numpy()[~mandatory]
        need=count-int(mandatory.sum())
        if need<0 or need>len(optional):raise ValueError('Ngân sách không giữ đủ điểm bắt buộc')
        keep[part.index.to_numpy()[mandatory]]=True
        if need:
            positions=np.linspace(0,len(optional)-1,need).round().astype(int)
            if len(np.unique(positions))!=need:raise ValueError('Vị trí lấy mẫu bị trùng')
            keep[optional[positions]]=True
    path=OUT/record['output'];path.parent.mkdir(parents=True,exist_ok=True)
    checksum=hashlib.sha256();rows=0;source_rows=0
    with gzip.open(FULL/record['output'],'rb') as source,gzip.open(path,'wb',compresslevel=6) as output:
        header=source.readline();output.write(header);checksum.update(header)
        for index,line in enumerate(source):
            if index>=len(keep):raise ValueError('Số dòng CSV không khớp')
            if keep[index]:output.write(line);checksum.update(line);rows+=1
            source_rows+=1
    if source_rows!=len(keep) or rows!=int(keep.sum()):raise ValueError('Số dòng xuất sai')
    verify=hashlib.sha256()
    with gzip.open(path,'rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):verify.update(block)
    if verify.hexdigest()!=checksum.hexdigest():raise ValueError('Nội dung dòng xuất không giữ nguyên')
    return dict(phase=record['phase'],battery=record['battery'],output=record['output'],
        source_rows=source_rows,selected_rows=rows,uncompressed_sha256=verify.hexdigest(),source_bytes_preserved=True)


def main():
    records=pd.read_csv(FULL/'source_preservation_audit.csv').to_dict('records')
    chunks=[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        tasks=[pool.submit(scan,record) for record in records]
        for i,task in enumerate(as_completed(tasks),1):
            chunks.append(task.result())
            if i%40==0:print('Đếm điểm bắt buộc',i,'/172',flush=True)
    cycles=pd.concat(chunks,ignore_index=True).sort_values(['phase','battery','cycle']).reset_index(drop=True)
    available=(cycles.rows-cycles.mandatory).to_numpy(dtype=np.int64)
    remaining=TARGET-int(cycles.mandatory.sum())
    if not 0<=remaining<=int(available.sum()):raise ValueError('Mục tiêu không phù hợp số mẫu bắt buộc')
    ideal=available*(remaining/int(available.sum()))
    extras=np.floor(ideal).astype(np.int64)
    deficit=remaining-int(extras.sum())
    order=np.argsort(-(ideal-extras),kind='stable')
    extras[order[:deficit]]+=1
    cycles['selected_rows']=cycles.mandatory+extras
    if int(cycles.selected_rows.sum())!=TARGET:raise ValueError('Tổng phân bổ không đúng')
    cycles.to_csv(OUT/'cycle_sampling_audit.csv',index=False)
    audits=[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        tasks=[]
        for record in records:
            part=cycles[(cycles.phase==record['phase'])&(cycles.battery==record['battery'])]
            budgets=dict(zip(part.cycle.astype(int),part.selected_rows.astype(int)))
            tasks.append(pool.submit(copy,record,budgets))
        for i,task in enumerate(as_completed(tasks),1):
            audits.append(task.result())
            if i%30==0:print('Xuất và đối chiếu nguyên văn',i,'/172',flush=True)
    audit=pd.DataFrame(audits)
    if int(audit.selected_rows.sum())!=TARGET:raise ValueError('Số dòng thực tế không đúng mục tiêu')
    audit.sort_values(['phase','battery']).to_csv(OUT/'source_preservation_audit.csv',index=False)
    # Bảng đặc trưng/nhãn giữ nguyên file từ bộ đầy đủ, không tính từ đoạn sau đã lấy thưa.
    for name in ['training_table.csv','cycle_features.csv','source_metadata.json']:
        shutil.copy2(FULL/name,OUT/name)
    original=json.loads((FULL/'dataset_summary.json').read_text())
    summary=dict(dataset='SDU 2025 — 10 million rows, all selected reference cycles',measurement_rows=TARGET,
        parent_measurement_rows=30929675,cycles=original['selected_cycles'],batteries=86,files=172,
        all_first_120s_samples_preserved=True,final_sample_of_each_cycle_preserved=True,
        all_parent_cycles_preserved=True,mandatory_samples=int(cycles.mandatory.sum()),
        feature_and_label_files_identical_to_parent=True,source_row_bytes_preserved=True,
        interpolation=False,signal_values_modified=False,applied_to_application=False,
        method='Keep every sample within 120s of first discharge and final sample of every cycle; distribute remaining budget proportionally to available later rows and sample evenly by chronological rank. Not a noise-removal claim.',
        source_doi=original['source_doi'],feature_columns=original['feature_columns'],nominal_capacity_ah=2.4)
    (OUT/'dataset_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    qc=BASE/'quality_review'
    for name in ['summary.json','spike_candidates.csv','audit_by_file.csv']:
        shutil.copy2(qc/name,OUT/('quality_'+name))
    text='''# SDU — bản 10 triệu dòng giữ đủ chu kỳ

10.000.000 dòng đo xả; 20.823 chu kỳ tham chiếu; 86 pin vật lý; 172 CSV gzip.

## Giữ và giảm những gì

Giữ đủ các chu kỳ trong bộ đã chọn 30.929.675 dòng. Giữ mọi điểm đo trong 120 giây đầu xả và điểm cuối mỗi chu kỳ. Ở phần sau, lấy thưa theo thứ tự thời gian; số điểm được phân bổ theo độ dài chu kỳ. Không bỏ pin hoặc chu kỳ để đạt số dòng.

Từng dòng CSV được chọn giữ nguyên văn, gồm tên cột, cách viết số và thứ tự nguồn. Không sửa giá trị, điền thiếu, nội suy hoặc nhân bản. Hai ZIP nguồn và bộ 30,9 triệu dòng vẫn giữ riêng. Tập con này do dự án tạo, không phải gói gốc của tác giả.

Bảng training_table.csv và cycle_features.csv giữ nguyên file từ bộ đầy đủ. Dung lượng tham chiếu/SOH được tính từ chu kỳ đầy đủ; không tính lại dung lượng bằng tích phân trên đường đã lấy thưa. Đặc trưng chỉ dùng 120 giây đầu, được giữ đủ điểm. Giảm mật độ sau 120 giây làm mất chi tiết ở đoạn đó; không phù hợp nếu nghiên cứu khác cần nguyên chuỗi toàn chu kỳ.

## Kiểm tra chất lượng

Đã kiểm tra 30.929.675 dòng: không thiếu/vô hạn ở các tín hiệu chính, không có dòng trùng hoàn toàn, không có khóa thời gian trùng và không có giá trị ngoài các giới hạn kiểm tra đã công bố. Có 28 bước thời gian đi lùi trong thứ tự nguồn; khi tính đặc trưng đã sắp xếp bản sao trong chu kỳ, không sửa thứ tự file nguồn.

Bộ kiểm tra tìm được 65 nghi vấn xung đơn điện áp và 14 nghi vấn nhiệt độ, theo quy tắc so sánh hai điểm lân cận khi dòng ổn định. Đây là cờ xem xét, chưa xác nhận lỗi cảm biến; không tự sửa hay loại những điểm này chỉ dựa trên quy tắc. Danh sách nằm trong quality_spike_candidates.csv. Bản 10 triệu dòng giảm mật độ đoạn sau cửa sổ mô hình; không tuyên bố đã loại hết nhiễu.

## Sử dụng

Huấn luyện bằng training_table.csv (20.823 hàng), lấy đúng feature_columns trong dataset_summary.json. Không dùng dung lượng toàn chu kỳ, số điểm đo hoặc thông tin cuối chu kỳ làm đầu vào. Chia tập theo Battery_ID vật lý qua cả hai giai đoạn. Đọc file đo từng pin hoặc từng khối; không nạp tất cả vào RAM.

Nguồn: https://zenodo.org/records/14859405 — DOI 10.5281/zenodo.14859405, công bố 2025, CC BY 4.0. Wang, Gao và Tian: Deep sorting of reused batteries for enabling long-term consistency grouping with unknown prior conditions. Pin NMC(532)/graphite Lishen LR1865SZ, danh định 2,4 Ah.

Chưa áp dụng vào ứng dụng và chưa chạy mô hình mới. Script tái tạo cần thư mục selection (bộ lớn) và quality_review ở thư mục cha.
'''
    (OUT/'README.md').write_text(text)
    output=BASE/'Dataset_SDU_10tr_dong.zip'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(OUT.iterdir()):
            if file.is_file():archive.write(file,'SDU_10tr/'+file.name)
        for file in sorted((OUT/'source_rows').rglob('*.csv.gz')):
            archive.write(file,'SDU_10tr/'+str(file.relative_to(OUT)),compress_type=zipfile.ZIP_STORED)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:raise ValueError('ZIP lỗi')
    checksum=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.sha256').write_text(checksum+'  '+output.name+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    print('ZIP',output.stat().st_size,'bytes',flush=True)


if __name__=='__main__':main()
