"""Kiểm tra bản 10 triệu dòng thực tế; không chỉnh sửa dữ liệu nguồn."""
import gzip
import hashlib
import io
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
import pandas as pd

DATA=Path(__file__).resolve().parents[1]
OUT=DATA/'verification'


def verify(record):
    path=DATA/record['output']
    with gzip.open(path,'rb') as stream:raw=stream.read()
    if hashlib.sha256(raw).hexdigest()!=record['uncompressed_sha256']:
        raise ValueError('SHA-256 không khớp: '+record['output'])
    frame=pd.read_csv(io.BytesIO(raw))
    core=['Test_Time(s)','Cycle_Index','Current(A)','Voltage(V)','Aux_Temperature_1(C)','Discharge_Capacity(Ah)','Battery_ID','Protocol_ID']
    if set(core)-set(frame):raise ValueError('Thiếu cột bắt buộc')
    finite=np.isfinite(frame[core].to_numpy(dtype=float)).all(axis=1)
    bounds=frame['Voltage(V)'].between(0,4.5,inclusive='right')&frame['Aux_Temperature_1(C)'].between(-40,100)&(frame['Test_Time(s)']>=0)&(frame['Discharge_Capacity(Ah)']>=-1e-6)
    cols=[c for c in frame if not c.startswith('Unnamed:')]
    duplicate=int(frame.duplicated(cols).sum())
    conflicts=int(frame.drop_duplicates(cols).duplicated(['Battery_ID','Cycle_Index','Test_Time(s)']).sum())
    if frame.Battery_ID.nunique()!=1 or int(frame.Battery_ID.iloc[0])!=record['battery']:raise ValueError('Sai mã pin')
    expected=pd.read_csv(DATA/'cycle_features.csv')
    expected=expected[(expected.phase==record['phase'])&(expected.battery==record['battery'])].set_index('cycle',drop=False)
    budgets=pd.read_csv(DATA/'cycle_sampling_audit.csv')
    budgets=budgets[(budgets.phase==record['phase'])&(budgets.battery==record['battery'])].set_index('cycle',drop=False)
    candidates=pd.read_csv(DATA/'quality_spike_candidates.csv')
    candidates=candidates[candidates.source_subset_file==record['output']]
    row_key=['Battery_ID','Cycle_Index','Test_Time(s)']
    present=candidates.merge(frame[row_key].drop_duplicates(),on=row_key,how='inner')
    feature_bad=0;label_bad=0;count_bad=0;window_rows=0;candidate_early=0;retained=[]
    for cycle,part in frame.groupby('Cycle_Index'):
        part=part.sort_values('Test_Time(s)')
        truth=expected.loc[int(cycle)]
        budget=budgets.loc[int(cycle)]
        count_bad+=int(len(part)!=int(budget.selected_rows))
        t=part['Test_Time(s)'].to_numpy();t=t-t.min()
        window=t<=120
        v=part['Voltage(V)'].to_numpy()[window];i=part['Current(A)'].to_numpy()[window];temp=part['Aux_Temperature_1(C)'].to_numpy()[window];tw=t[window]
        window_rows+=int(window.sum())
        def slope(y):
            centered=tw-tw.mean()
            return np.dot(centered,y-y.mean())/np.dot(centered,centered)
        actual=dict(phase_code=0 if record['phase']=='primary' else 1,cycle=int(cycle),
            voltage_mean=v.mean(),voltage_min=v.min(),voltage_max=v.max(),voltage_std=v.std(),voltage_slope=slope(v),
            current_mean=i.mean(),current_std=i.std(),temperature_mean=temp.mean(),temperature_max=temp.max(),temperature_slope=slope(temp))
        feature_bad+=int(not all(np.isclose(value,truth[key],atol=1e-10,rtol=1e-10) for key,value in actual.items()))
        label_bad+=int(not np.isclose(part['Discharge_Capacity(Ah)'].max(),truth.capacity_ah,atol=1e-10,rtol=1e-10))
        flags=present[present.Cycle_Index==cycle].copy()
        if len(flags):
            flags['relative_time_s']=flags['Test_Time(s)']-part['Test_Time(s)'].min()
            flags['in_model_window']=flags.relative_time_s<=120
            candidate_early+=int(flags.in_model_window.sum())
            retained.append(flags)
    backward=int((frame.groupby('Cycle_Index')['Test_Time(s)'].diff()<0).sum())
    audit=dict(phase=record['phase'],battery=record['battery'],file=record['output'],rows=len(frame),cycles=frame.Cycle_Index.nunique(),
        missing_or_nonfinite_rows=int((~finite).sum()),outside_limits_rows=int((~bounds).sum()),exact_duplicates=duplicate,
        duplicate_time_keys=conflicts,source_hash_verified=True,feature_mismatch_cycles=feature_bad,label_mismatch_cycles=label_bad,
        sample_count_mismatch_cycles=count_bad,first120s_rows=window_rows,backward_time_steps=backward,
        retained_parent_spike_candidates=len(present),spike_candidates_first120s=candidate_early)
    return audit,pd.concat(retained,ignore_index=True) if retained else pd.DataFrame()


def main():
    source=pd.read_csv(DATA/'source_preservation_audit.csv')
    audits,flags=[],[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        tasks=[pool.submit(verify,row) for row in source.to_dict('records')]
        for done,task in enumerate(as_completed(tasks),1):
            audit,flag=task.result();audits.append(audit)
            if len(flag):flags.append(flag)
            if done%30==0:print('Đã kiểm tra thực tế',done,'/172 file',flush=True)
    audit=pd.DataFrame(audits)
    audit.sort_values(['phase','battery']).to_csv(OUT/'audit_by_file.csv',index=False)
    pd.concat(flags,ignore_index=True).to_csv(OUT/'retained_spike_candidates.csv',index=False) if flags else (OUT/'retained_spike_candidates.csv').write_text('source_subset_file\n')
    keys=['rows','cycles','missing_or_nonfinite_rows','outside_limits_rows','exact_duplicates','duplicate_time_keys',
        'feature_mismatch_cycles','label_mismatch_cycles','sample_count_mismatch_cycles','first120s_rows','backward_time_steps',
        'retained_parent_spike_candidates','spike_candidates_first120s']
    result={key:int(audit[key].sum()) for key in keys}
    fatal=['missing_or_nonfinite_rows','outside_limits_rows','exact_duplicates','duplicate_time_keys','feature_mismatch_cycles','label_mismatch_cycles','sample_count_mismatch_cycles']
    result.update(files=len(audit),physical_batteries=int(audit.battery.nunique()),all_source_hashes_match=bool(audit.source_hash_verified.all()),
        structural_validation_passed=bool(not any(result[key] for key in fatal)),
        status='Structurally checked; suspected spikes retained for review; no claim of zero noise',source_data_modified=False)
    if result['rows']!=10000000 or result['cycles']!=20823 or result['physical_batteries']!=86:raise ValueError('Sai quy mô')
    (OUT/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
