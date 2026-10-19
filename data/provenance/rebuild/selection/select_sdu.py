"""Chọn chu kỳ xả tham chiếu 0,2C của SDU, không nội suy và không sửa số đo.

Đọc từng file CSV trong ZIP; xuất CSV gzip theo pin để phù hợp RAM 16 GB.
"""
import gzip
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

OUT=Path(__file__).resolve().parent
BASE=OUT.parent
USE=['Test_Time(s)','Cycle_Index','Current(A)','Voltage(V)','Discharge_Capacity(Ah)',
     'Aux_Temperature_1(C)','Battery_ID','Protocol_ID']
NOMINAL_AH=2.4
FEATURES=['phase_code','cycle','voltage_mean','voltage_min','voltage_max','voltage_std',
          'voltage_slope','current_mean','current_std','temperature_mean','temperature_max','temperature_slope']


def slope(t,y):
    centered=t-t.mean()
    return float(np.dot(centered,y-y.mean())/np.dot(centered,centered))


def classify(part):
    """Điều kiện chọn cố định, không dựa trên độ đẹp của đường SOH."""
    active=part.loc[part['Current(A)']<-.1].copy()
    if active.empty:return None,'Không có mẫu xả chủ động'
    current=active['Current(A)'].to_numpy()
    if abs(np.median(current)+.48)>.03:
        return None,'Không thuộc nhóm xả tham chiếu 0,2C'
    if np.mean(np.abs(current+.48)<=.03)<.95:
        return None,'Dòng xả không ổn định theo tiêu chí tham chiếu'
    active=active.sort_values('Test_Time(s)',kind='stable')
    values=active[USE].to_numpy(dtype=float)
    if not np.isfinite(values).all():return None,'Thiếu/vô hạn ở tín hiệu bắt buộc'
    if active['Test_Time(s)'].duplicated().any():return None,'Thời gian xả xung đột'
    t=active['Test_Time(s)'].to_numpy();v=active['Voltage(V)'].to_numpy()
    temperature=active['Aux_Temperature_1(C)'].to_numpy()
    q=active['Discharge_Capacity(Ah)'].to_numpy()
    if not ((v>0)&(v<=4.5)).all():return None,'Điện áp ngoài miền kiểm tra 0–4,5 V'
    if not ((temperature>=-40)&(temperature<=100)).all():return None,'Nhiệt độ ngoài miền kiểm tra'
    if v[0]<4.0:return None,'Không đủ điện áp đầu xả tham chiếu'
    if not 2.95<=v[-1]<=3.05:return None,'Chưa xác nhận xả kết thúc gần 3 V'
    if (np.diff(q)<-1e-4).any():return None,'Dung lượng tích lũy giảm bất thường trong đoạn xả'
    capacity=float(q.max())
    if not 0<capacity<=NOMINAL_AH*1.2:return None,'Dung lượng tham chiếu không hợp lệ'
    if q[0]>.01:return None,'Dung lượng tích lũy không bắt đầu gần 0 Ah'
    elapsed=t-t[0]
    integrated=float(np.trapezoid(-active['Current(A)'].to_numpy(),elapsed)/3600)
    # Kiểm tra nhãn với tích phân dòng, không thay nhãn bằng kết quả tích phân.
    if abs(integrated-capacity)>max(.02,.02*capacity):
        return None,'Dung lượng không khớp tích phân dòng trong sai số 2% hoặc 0,02 Ah'
    if len(elapsed)<5 or elapsed[-1]<120:return None,'Đoạn xả quá ngắn'
    window=elapsed<=120
    if window.sum()<5 or elapsed[window].max()<90:return None,'Không đủ cửa sổ 120 giây đầu'
    active['time_s']=elapsed
    return (active,capacity,integrated),'Đạt'


def main():
    OUT.mkdir(exist_ok=True)
    measurements=OUT/'measurements'
    measurements.mkdir(exist_ok=True)
    metadata_path=OUT/'source_metadata.json'
    if not metadata_path.exists():metadata_path=BASE/'zenodo_record.json'
    metadata=json.loads(metadata_path.read_text())
    selected,rejected,audits=[],[],[]
    for phase_code,name in enumerate(['Primary_use_phase.zip','Second_life_phase.zip']):
        source=next(x for x in metadata['files'] if x['key']==name)
        path=BASE/name
        md5=hashlib.md5()
        with path.open('rb') as f:
            for block in iter(lambda:f.read(4*1024*1024),b''):md5.update(block)
        if 'md5:'+md5.hexdigest()!=source['checksum']:raise ValueError('Sai MD5 nguồn: '+name)
        phase='primary' if phase_code==0 else 'second_life'
        with zipfile.ZipFile(path) as archive:
            files=sorted(n for n in archive.namelist() if n.endswith('.csv'))
            for index,filename in enumerate(files,1):
                with archive.open(filename) as stream:
                    frame=pd.read_csv(stream,usecols=USE)
                if frame.Battery_ID.nunique()!=1:raise ValueError('File có nhiều mã pin: '+filename)
                battery=int(frame.Battery_ID.iloc[0])
                output=measurements/f'{phase}_pin_{battery:02d}.csv.gz'
                temp=output.with_suffix('.tmp')
                kept_rows,kept_cycles=0,0
                with gzip.open(temp,'wt',encoding='utf-8',newline='',compresslevel=1) as stream:
                    for cycle,part in frame.groupby('Cycle_Index',sort=True):
                        part=part.copy()
                        # source_row giữ số thứ tự dòng dữ liệu gốc, bắt đầu từ 0.
                        part['source_row']=part.index
                        result,reason=classify(part)
                        if result is None:
                            rejected.append(dict(phase=phase,battery=battery,cycle=int(cycle),source_file=filename,reason=reason))
                            continue
                        active,capacity,integrated=result
                        t=active.time_s.to_numpy();window=t<=120
                        v=active['Voltage(V)'].to_numpy()[window]
                        i=active['Current(A)'].to_numpy()[window]
                        temperature=active['Aux_Temperature_1(C)'].to_numpy()[window]
                        tw=t[window]
                        row=dict(battery=battery,phase=phase,phase_code=phase_code,cycle=int(cycle),
                            source_file=filename,protocol_id=int(part.Protocol_ID.iloc[0]),
                            capacity_ah=capacity,soh_pct=capacity/NOMINAL_AH*100,
                            integrated_capacity_ah=integrated,measurement_rows=len(active),
                            start_voltage_v=float(active['Voltage(V)'].iloc[0]),end_voltage_v=float(active['Voltage(V)'].iloc[-1]),
                            voltage_mean=float(v.mean()),voltage_min=float(v.min()),voltage_max=float(v.max()),
                            voltage_std=float(v.std()),voltage_slope=slope(tw,v),
                            current_mean=float(i.mean()),current_std=float(i.std()),
                            temperature_mean=float(temperature.mean()),temperature_max=float(temperature.max()),
                            temperature_slope=slope(tw,temperature))
                        selected.append(row)
                        data=pd.DataFrame(dict(phase=phase,battery=battery,cycle=int(cycle),source_file=filename,
                            source_row=active.source_row.to_numpy(),time_in_test_s=active['Test_Time(s)'].to_numpy(),
                            time_s=t,voltage_v=active['Voltage(V)'].to_numpy(),current_a=active['Current(A)'].to_numpy(),
                            temperature_c=active['Aux_Temperature_1(C)'].to_numpy(),
                            discharge_capacity_ah=active['Discharge_Capacity(Ah)'].to_numpy()))
                        data.to_csv(stream,index=False,header=kept_cycles==0)
                        kept_cycles+=1;kept_rows+=len(data)
                if kept_cycles:
                    temp.replace(output)
                else:
                    temp.unlink()
                audits.append(dict(phase=phase,battery=battery,source_file=filename,source_rows=len(frame),
                    source_cycles=frame.Cycle_Index.nunique(),selected_cycles=kept_cycles,selected_discharge_rows=kept_rows))
                pd.DataFrame(audits).to_csv(OUT/'audit_by_file.csv',index=False)
                print(f'{phase} {index}/{len(files)}: pin {battery}, {kept_cycles} chu kỳ, {kept_rows:,} dòng',flush=True)
    cycles=pd.DataFrame(selected)
    exclusions=pd.DataFrame(rejected)
    audit=pd.DataFrame(audits)
    cycles.to_csv(OUT/'cycle_features.csv',index=False)
    exclusions.to_csv(OUT/'excluded_cycles.csv',index=False)
    exclusions.groupby(['phase','reason']).size().rename('cycles').reset_index().to_csv(OUT/'exclusion_summary.csv',index=False)
    summary=dict(dataset='SDU 2025 — selected reference-condition discharge cycles',source_doi=metadata['doi'],
        nominal_capacity_ah=NOMINAL_AH,unique_batteries=cycles.battery.nunique(),
        source_measurement_rows=int(audit.source_rows.sum()),source_cycles=int(audit.source_cycles.sum()),
        selected_measurement_rows=int(audit.selected_discharge_rows.sum()),selected_cycles=len(cycles),
        phases=cycles.groupby('phase').agg(batteries=('battery','nunique'),cycles=('cycle','size'),measurement_rows=('measurement_rows','sum')).reset_index().to_dict('records'),
        feature_columns=FEATURES,target='soh_pct = capacity_ah / 2.4 * 100',
        min_soh_pct=float(cycles.soh_pct.min()),max_soh_pct=float(cycles.soh_pct.max()),
        interpolation=False,replication=False,signal_values_modified=False,
        selected_scope='All recorded active-discharge samples (I < -0.1 A) of accepted 0.2C reference-condition cycles; charge/rest and other operating regimes excluded. Operational cycles sharing the reference condition can be retained.',
        identification='Median discharge current within 0.03 A of -0.48 A; >=95% samples within that band; start voltage >=4.0V and end 2.95–3.05V; capacity integrity checks',
        split_warning='Group by physical battery across both phases. Same battery cannot appear in train and test of the same new-battery evaluation fold.',
        applied_to_application=False)
    (OUT/'dataset_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
