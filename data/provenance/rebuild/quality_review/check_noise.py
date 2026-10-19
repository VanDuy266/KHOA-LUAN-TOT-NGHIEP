"""Kiểm tra lỗi rõ ràng và đánh dấu xung đơn để xem xét; không sửa số đo."""
import json
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
import numpy as np
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
FULL=BASE/'selection'
OUT=BASE/'quality_review'
CORE=['Test_Time(s)','Cycle_Index','Current(A)','Voltage(V)','Aux_Temperature_1(C)','Discharge_Capacity(Ah)','Battery_ID']


def check(record):
    path=FULL/record['output']
    frame=pd.read_csv(path)
    values=frame[CORE].to_numpy(dtype=float)
    finite=np.isfinite(values).all(axis=1)
    bounds=(frame['Test_Time(s)']>=0)&frame['Voltage(V)'].between(0,4.5,inclusive='right')&frame['Aux_Temperature_1(C)'].between(-40,100)&(frame['Discharge_Capacity(Ah)']>=-1e-6)
    invalid=~finite|~bounds.to_numpy()
    columns=[c for c in frame if not c.startswith('Unnamed:')]
    duplicates=frame.duplicated(columns)
    conflicts=frame.drop_duplicates(columns).duplicated(['Battery_ID','Cycle_Index','Test_Time(s)'])
    backward=int((frame.groupby(['Battery_ID','Cycle_Index'])['Test_Time(s)'].diff()<0).sum())
    ordered=frame.sort_values(['Cycle_Index','Test_Time(s)'])
    t=ordered['Test_Time(s)'].to_numpy();cycle=ordered.Cycle_Index.to_numpy()
    voltage=ordered['Voltage(V)'].to_numpy();current=ordered['Current(A)'].to_numpy();temperature=ordered['Aux_Temperature_1(C)'].to_numpy()
    same=(cycle[:-2]==cycle[1:-1])&(cycle[1:-1]==cycle[2:])
    dt1=t[1:-1]-t[:-2];dt2=t[2:]-t[1:-1]
    near=same&(dt1>0)&(dt2>0)&(dt1<=20)&(dt2<=20)
    stable=(np.abs(current[1:-1]-current[:-2])<.03)&(np.abs(current[1:-1]-current[2:])<.03)
    v_spike=near&stable&(np.abs(voltage[1:-1]-(voltage[:-2]+voltage[2:])/2)>.15)&(np.abs(voltage[:-2]-voltage[2:])<.03)
    temp_spike=near&stable&(np.abs(temperature[1:-1]-(temperature[:-2]+temperature[2:])/2)>3)&(np.abs(temperature[:-2]-temperature[2:])<.2)
    candidates=ordered.iloc[np.flatnonzero(v_spike|temp_spike)+1].copy()
    candidates['source_subset_file']=record['output']
    errors=frame.loc[invalid|duplicates.to_numpy()].copy()
    errors['source_subset_file']=record['output']
    audit=dict(phase=record['phase'],battery=record['battery'],file=record['output'],rows=len(frame),
        nonfinite_rows=int((~finite).sum()),outside_limits_rows=int((~bounds).sum()),
        exact_duplicate_rows=int(duplicates.sum()),conflicting_time_keys=int(conflicts.sum()),
        backward_time_steps=backward,voltage_spike_candidates=int(v_spike.sum()),temperature_spike_candidates=int(temp_spike.sum()))
    return audit,candidates,errors


def main():
    source=pd.read_csv(FULL/'source_preservation_audit.csv')
    audits,candidates,errors=[],[],[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        tasks=[pool.submit(check,row) for row in source.to_dict('records')]
        for task in as_completed(tasks):
            audit,candidate,error=task.result();audits.append(audit)
            if len(candidate):candidates.append(candidate)
            if len(error):errors.append(error)
            if len(audits)%20==0:print('Đã kiểm tra',len(audits),'/172 file',flush=True)
    audit=pd.DataFrame(audits)
    audit.sort_values(['phase','battery']).to_csv(OUT/'audit_by_file.csv',index=False)
    pd.concat(candidates,ignore_index=True).to_csv(OUT/'spike_candidates.csv',index=False) if candidates else (OUT/'spike_candidates.csv').write_text('source_subset_file\n')
    pd.concat(errors,ignore_index=True).to_csv(OUT/'definite_errors.csv',index=False) if errors else (OUT/'definite_errors.csv').write_text('source_subset_file\n')
    keys=['rows','nonfinite_rows','outside_limits_rows','exact_duplicate_rows','conflicting_time_keys','backward_time_steps','voltage_spike_candidates','temperature_spike_candidates']
    summary={key:int(audit[key].sum()) for key in keys}
    summary.update(files=len(audit),batteries=int(audit.battery.nunique()),source_files_modified=False,
        spike_policy='Heuristic candidates for review only; not automatically removed. Similar consecutive values are not classified as errors.',
        input_features='Use only feature_columns in selection/dataset_summary.json. Energy, internal resistance, export index, source identifiers and whole-cycle target checks are not model inputs.')
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
