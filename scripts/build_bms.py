"""Build and evaluate the on-road BAIC BMS experiment from verified RAR archives.

Run from project root with .venv/Scripts/python.exe scripts/build_bms.py.
No external source code is executed. tar.exe only streams CSV data.
"""
from pathlib import Path
import sys, json, subprocess, time
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.dummy import DummyRegressor
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from battery_soh.bms import FEATURES,NOMINAL_AH,charging_features,tail_capacity
from battery_soh.hybrid import RidgeResidualForest

COLUMNS=['number','record_time','soc','pack_voltage','charge_current','max_cell_voltage',
         'min_cell_voltage','max_temperature','min_temperature','available_energy','available_capacity']

def process_archive(i):
    raw=ROOT/f'data/bms/raw/vehicle_{i:02d}.rar'
    pipe=subprocess.Popen(['tar.exe','-xOf',str(raw),f'#{i}.csv'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        frame=pd.read_csv(pipe.stdout)
    finally:
        pipe.stdout.close()
    stderr=pipe.stderr.read().decode(errors='replace'); code=pipe.wait()
    if code: raise RuntimeError(stderr)
    if len(frame.columns)!=len(COLUMNS): raise ValueError('Unexpected CSV columns')
    frame.columns=COLUMNS
    count=len(frame)
    frame['timestamp']=pd.to_datetime(frame.record_time.astype(str),format='%Y%m%d%H%M%S',errors='coerce')
    frame=frame.sort_values('timestamp',kind='stable')
    duplicate=int(frame.timestamp.duplicated(keep=False).sum())
    frame=frame[frame.timestamp.notna() & ~frame.timestamp.duplicated(keep=False)].copy()
    for col in COLUMNS[2:9]: frame[col]=pd.to_numeric(frame[col],errors='coerce')
    # Invalid rows break continuity instead of being interpolated into apparently complete sessions.
    valid=np.isfinite(frame[COLUMNS[2:9]]).all(axis=1)
    valid &= frame.soc.between(0,100) & frame.pack_voltage.between(200,450)
    valid &= frame.min_cell_voltage.between(2,4.5) & frame.max_cell_voltage.between(2,4.5)
    valid &= (frame.max_cell_voltage>=frame.min_cell_voltage)
    valid &= frame.min_temperature.between(-30,85) & frame.max_temperature.between(-30,85)
    valid &= (frame.max_temperature>=frame.min_temperature) & frame.charge_current.between(-300,0)
    invalid=int((~valid).sum())
    frame=frame[valid].copy()
    gap=frame.timestamp.diff().dt.total_seconds()
    frame['session']=(gap.isna() | (gap>10) | (gap<=0)).cumsum()
    rows=[]; windows=[]; reasons={}; demo=None
    for session,part in frame.groupby('session',sort=False):
        part=part.copy()
        part['time_s']=(part.timestamp-part.timestamp.iloc[0]).dt.total_seconds()
        why=None
        if len(part)<116: why='short_session'
        elif (part.soc.diff().dropna() < -0.1).any() or (part.soc.diff().dropna()>2).any(): why='soc_jump'
        elif (part.charge_current<0).mean()<0.95: why='not_continuous_charging'
        first=part[part.time_s<=120]
        if why is None and (len(first)<12 or first.time_s.iloc[-1]<112): why='incomplete_120s_window'
        capacity=None
        if why is None:
            try: capacity=tail_capacity(part)
            except ValueError: why='insufficient_tail_soc_or_samples'
        if why is None and not (0<capacity<=NOMINAL_AH*1.3): why='invalid_capacity_reference'
        if why:
            reasons[why]=reasons.get(why,0)+1; continue
        vehicle=f'BAIC_{i:02d}'
        row=dict(vehicle=vehicle,session=int(session),start=part.timestamp.iloc[0].isoformat(),
                 month=part.timestamp.iloc[0].strftime('%Y-%m'),samples=len(part),
                 tail_capacity_ah=capacity,**charging_features(first))
        rows.append(row)
        window=first[['time_s','soc','pack_voltage','charge_current','max_cell_voltage',
                      'min_cell_voltage','max_temperature','min_temperature']].copy()
        window['vehicle']=vehicle;window['session']=session;windows.append(window)
        if demo is None:
            demo=part[['time_s','soc','pack_voltage','charge_current','max_cell_voltage',
                       'min_cell_voltage','max_temperature','min_temperature']].iloc[:1200].copy()
    if demo is not None: demo.to_csv(ROOT/f'data/bms/processed/{i:02d}_example.csv.gz',index=False)
    audit=dict(vehicle=f'BAIC_{i:02d}',raw_rows=count,duplicate_timestamp_rows=duplicate,
               invalid_rows=invalid,sessions=int(frame.session.nunique()),eligible_sessions=len(rows),
               first_time=frame.timestamp.min().isoformat(),last_time=frame.timestamp.max().isoformat(),excluded=reasons)
    print(f'{audit["vehicle"]}: {count:,} rows, {len(rows)} eligible sessions',flush=True)
    return rows,windows,audit

def score(actual,predicted):
    return dict(mae=mean_absolute_error(actual,predicted),rmse=float(np.sqrt(mean_squared_error(actual,predicted))),
                r2=r2_score(actual,predicted) if len(actual)>1 else None)

def main():
    rows=[];windows=[];audits=[]
    for i in range(1,21):
        r,w,a=process_archive(i);rows.extend(r);windows.extend(w);audits.append(a)
    frame=pd.DataFrame(rows)
    monthly=frame.groupby(['vehicle','month']).tail_capacity_ah.agg(['median','count']).reset_index()
    monthly=monthly.rename(columns={'median':'reference_capacity_ah','count':'reference_sessions'})
    monthly=monthly[monthly.reference_sessions>=3]
    frame=frame.merge(monthly,on=['vehicle','month'],how='inner',validate='many_to_one')
    frame['reference_soh_pct']=frame.reference_capacity_ah/NOMINAL_AH*100
    frame.to_csv(ROOT/'reports/bms/features.csv',index=False)
    monthly.to_csv(ROOT/'reports/bms/monthly_reference.csv',index=False)
    # All windows retain their session key; display is filtered against eligible labeled sessions in the UI.
    pd.concat(windows,ignore_index=True).to_parquet(ROOT/'data/bms/processed/windows.parquet',index=False)
    x=frame[FEATURES];y=frame.reference_soh_pct
    factories={'Mean baseline':lambda:DummyRegressor(), 'Ridge':lambda:make_pipeline(StandardScaler(),Ridge(alpha=10)),
               'Random Forest':lambda:RandomForestRegressor(n_estimators=100,max_depth=12,min_samples_leaf=5,n_jobs=2,random_state=42),
               'Ridge-RF residual':lambda:RidgeResidualForest()}
    predictions=[];timings=[];by_vehicle=[]
    for fold,(train,test) in enumerate(GroupKFold(5).split(x,y,groups=frame.vehicle),1):
        assert not set(frame.vehicle.iloc[train]) & set(frame.vehicle.iloc[test])
        for name,factory in factories.items():
            fitted=factory();t=time.perf_counter();fitted.fit(x.iloc[train],y.iloc[train]);fit=time.perf_counter()-t
            t=time.perf_counter();pred=fitted.predict(x.iloc[test]);duration=time.perf_counter()-t
            part=frame.iloc[test][['vehicle','session','start','month','reference_soh_pct']].copy()
            part['prediction']=pred;part['fold']=fold;part['model']=name;predictions.append(part)
            timings.append(dict(model=name,fold=fold,fit_seconds=fit,predict_seconds=duration,n_train=len(train),n_test=len(test)))
            for vehicle,group in part.groupby('vehicle'):
                by_vehicle.append(dict(model=name,vehicle=vehicle,fold=fold,n_test=len(group),**score(group.reference_soh_pct,group.prediction)))
            print(f'Fold {fold}: {name} complete',flush=True)
    by_vehicle=pd.DataFrame(by_vehicle)
    summary=by_vehicle.groupby('model',sort=False)[['mae','rmse','r2']].mean().reset_index()
    summary.to_csv(ROOT/'reports/bms/metrics_summary.csv',index=False)
    by_vehicle.to_csv(ROOT/'reports/bms/metrics_by_vehicle.csv',index=False)
    pd.concat(predictions).to_csv(ROOT/'reports/bms/predictions.csv',index=False)
    pd.DataFrame(timings).to_csv(ROOT/'reports/bms/timings.csv',index=False)
    for name in ['Random Forest','Ridge-RF residual']:
        fitted=factories[name]();fitted.fit(x,y)
        joblib.dump(dict(model=fitted,features=FEATURES,dataset='BAIC BMS',target='field-derived monthly capacity / 145 Ah * 100',
                         training_min=x.min().to_dict(),training_max=x.max().to_dict()),
                    ROOT/('artifacts/bms/random_forest.joblib' if name=='Random Forest' else 'artifacts/bms/ridge_residual_forest.joblib'))
    result=dict(dataset='BAIC EU500 BMS',source_vehicles=20,vehicles=int(frame.vehicle.nunique()),raw_rows=sum(a['raw_rows'] for a in audits),
                sessions=len(frame),monthly_labels=len(monthly),nominal_capacity_ah=NOMINAL_AH,window_seconds=120,
                label_type='Field-derived proxy; not independent laboratory capacity',
                label_method='Median of charging-tail integral / SOC gain for vehicle-month; at least 3 sessions; tail starts after 120 seconds; SOC gain >=20 pp',
                validation='5-fold GroupKFold held-out vehicles; macro mean over vehicles; proxy-label agreement only',
                exclusions='No available_capacity, available_energy, timestamps, vehicle IDs or reference labels in feature matrix',
                audit=audits)
    (ROOT/'reports/bms/dataset_summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(summary.to_string(index=False),flush=True)
    print('BMS BUILD COMPLETE',flush=True)
if __name__=='__main__': main()
