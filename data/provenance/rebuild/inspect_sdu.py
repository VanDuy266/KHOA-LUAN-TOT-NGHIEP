"""Kiểm tra dữ liệu gốc SDU; không thay đổi mã nguồn dự án."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

FOLDER=Path(__file__).resolve().parent
CORE=['Test_Time(s)','Cycle_Index','Current(A)','Voltage(V)',
      'Charge_Capacity(Ah)','Discharge_Capacity(Ah)','Aux_Temperature_1(C)','Battery_ID','Protocol_ID']


def md5(path):
    h=hashlib.md5()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return 'md5:'+h.hexdigest()


def inspect_phase(name):
    record=json.loads((FOLDER/'zenodo_record.json').read_text())
    source=next(f for f in record['files'] if f['key']==name)
    path=FOLDER/name
    if path.stat().st_size!=source['size'] or md5(path)!=source['checksum']:
        raise ValueError('File không khớp MD5: '+name)
    phase=path.stem
    output=FOLDER/'inspection'
    output.mkdir(exist_ok=True)
    audits,labels,identity=[],[],[]
    with zipfile.ZipFile(path) as z:
        names=sorted(n for n in z.namelist() if n.lower().endswith('.csv'))
        for index,filename in enumerate(names,1):
            with z.open(filename) as stream:
                frame=pd.read_csv(stream,low_memory=False)
            missing_columns=sorted(set(CORE)-set(frame.columns))
            row=dict(phase=phase,file=filename,rows=len(frame),missing_columns='; '.join(missing_columns))
            if missing_columns:
                audits.append(row)
                print('Thiếu cột',filename,missing_columns,flush=True)
                continue
            values=frame[CORE].apply(pd.to_numeric,errors='coerce')
            row['missing_required_values']=int(values.isna().sum().sum())
            row['internal_resistance_missing_rows']=int(pd.to_numeric(frame['Internal_Resistance(Ohm)'],errors='coerce').isna().sum()) if 'Internal_Resistance(Ohm)' in frame else len(frame)
            for column in CORE:
                row['missing_'+column]=int(values[column].isna().sum())
            finite=np.isfinite(values.to_numpy()).all(axis=1)
            row['nonfinite_required_rows']=int((~finite).sum())
            row['negative_time_rows']=int((values['Test_Time(s)']<0).sum())
            row['noninteger_cycle_rows']=int((values.Cycle_Index.dropna()%1!=0).sum())
            row['nonpositive_cycle_rows']=int((values.Cycle_Index<=0).sum())
            row['voltage_outside_0_5V_rows']=int((~values['Voltage(V)'].between(0,5)).sum())
            row['temperature_outside_minus40_100C_rows']=int((~values['Aux_Temperature_1(C)'].between(-40,100)).sum())
            row['negative_capacity_rows']=int((values[['Charge_Capacity(Ah)','Discharge_Capacity(Ah)']]< -1e-6).any(axis=1).sum())
            # Bỏ cột chỉ số xuất CSV; giữ các cột thực sự đo và mã pin/giao thức.
            real_columns=[c for c in frame.columns if not c.startswith('Unnamed:')]
            row['exact_duplicate_rows']=int(frame.duplicated(real_columns).sum())
            unique=frame.drop_duplicates(real_columns)
            row['conflicting_time_keys']=int(unique.duplicated(['Battery_ID','Cycle_Index','Test_Time(s)']).sum())
            row['backward_time_rows']=int((values.groupby(['Battery_ID','Cycle_Index'],sort=False)['Test_Time(s)'].diff()<0).sum())
            row['temperature_min']=float(values['Aux_Temperature_1(C)'].min())
            row['temperature_max']=float(values['Aux_Temperature_1(C)'].max())
            row['temperature_distinct']=int(values['Aux_Temperature_1(C)'].nunique())
            row['cycles']=int(values.groupby(['Battery_ID','Cycle_Index']).ngroups)
            row['battery_ids']=';'.join(str(x) for x in sorted(values.Battery_ID.dropna().unique()))
            for battery in values.Battery_ID.dropna().unique():
                identity.append(dict(phase=phase,file=filename,battery_id=battery))
            row['cycles_positive_discharge_capacity']=0
            row['cycles_with_120s_voltage_current_temperature']=0
            row['cycles_without_complete_120s_window']=0
            row['cycles_with_missing_discharge_temperature']=0
            for (battery,cycle),part in values.groupby(['Battery_ID','Cycle_Index'],sort=False):
                discharge=part.loc[part['Current(A)']<-.01]
                if discharge.empty:
                    continue
                capacity=float(discharge['Discharge_Capacity(Ah)'].max())
                if not np.isfinite(capacity) or capacity<=0:
                    continue
                row['cycles_positive_discharge_capacity']+=1
                elapsed=discharge['Test_Time(s)']-discharge['Test_Time(s)'].iloc[0]
                window=discharge.loc[elapsed.between(0,120)]
                valid_window=(len(window)>=5 and elapsed.loc[window.index].max()>=90
                    and np.isfinite(window[['Test_Time(s)','Current(A)','Voltage(V)','Aux_Temperature_1(C)']].to_numpy()).all()
                    and not window['Test_Time(s)'].duplicated().any())
                row['cycles_with_120s_voltage_current_temperature']+=int(valid_window)
                row['cycles_without_complete_120s_window']+=int(not valid_window)
                row['cycles_with_missing_discharge_temperature']+=int(discharge['Aux_Temperature_1(C)'].isna().any())
                labels.append(dict(phase=phase,file=filename,battery_id=battery,cycle=cycle,
                    discharge_capacity_ah=capacity,discharge_rows=len(discharge),
                    discharge_span_s=float(elapsed.max()),valid_120s_window=bool(valid_window),
                    final_discharge_voltage_v=float(discharge['Voltage(V)'].iloc[-1]),
                    charge_capacity_max_ah=float(part['Charge_Capacity(Ah)'].max()),
                    discharge_temperature_min_c=float(discharge['Aux_Temperature_1(C)'].min()),
                    discharge_temperature_max_c=float(discharge['Aux_Temperature_1(C)'].max())))
            audits.append(row)
            print(f'{phase}: {index}/{len(names)} · {filename} · {len(frame):,} dòng · {row["cycles"]} chu kỳ',flush=True)
            # Nhật ký từng file để có thể xem ngay và không mất kết quả nếu bị ngắt.
            pd.DataFrame(audits).to_csv(output/f'{phase}_files.csv',index=False)
    audit=pd.DataFrame(audits)
    label_frame=pd.DataFrame(labels)
    identities=pd.DataFrame(identity)
    label_frame.to_csv(output/f'{phase}_cycles.csv',index=False)
    identities.to_csv(output/f'{phase}_identities.csv',index=False)
    count_columns=['rows','internal_resistance_missing_rows','missing_required_values','nonfinite_required_rows','negative_time_rows',
        'noninteger_cycle_rows','nonpositive_cycle_rows','voltage_outside_0_5V_rows',
        'temperature_outside_minus40_100C_rows','negative_capacity_rows','exact_duplicate_rows',
        'conflicting_time_keys','backward_time_rows','cycles','cycles_positive_discharge_capacity',
        'cycles_with_120s_voltage_current_temperature','cycles_without_complete_120s_window',
        'cycles_with_missing_discharge_temperature']
    summary={column:int(audit[column].fillna(0).sum()) for column in count_columns if column in audit}
    summary.update(phase=phase,csv_files=len(names),files_missing_required_columns=int(audit.missing_columns.ne('').sum()),
        distinct_battery_ids=int(identities.battery_id.nunique()) if len(identities) else 0,
        battery_ids_in_multiple_files=int((identities.groupby('battery_id').file.nunique()>1).sum()) if len(identities) else 0,
        temperature_min=float(audit.temperature_min.min()),temperature_max=float(audit.temperature_max.max()),
        positive_capacity_min_ah=float(label_frame.discharge_capacity_ah.min()),
        positive_capacity_max_ah=float(label_frame.discharge_capacity_ah.max()),
        archive_md5_verified=source['checksum'],status='inspected_raw_data_not_applied_to_project',
        note='Candidate windows require >=5 active discharge samples spanning >=90s within first 120s. These counts do not establish completed full-discharge labels or certify vehicle deployment.')
    (output/f'{phase}_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['Primary_use_phase.zip','Second_life_phase.zip'])
    args=parser.parse_args()
    inspect_phase(args.phase)
