"""Reproducible descriptive SHAP and full-discharge ICA/DVA; no change to SOH predictor."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import pandas as pd
from scipy.integrate import cumulative_trapezoid
from scipy.signal import savgol_filter
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'app')]
from webapp.data import table,artifact,cycle_measurements
from battery_soh.features import FEATURES
from catboost import Pool


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def curves(frame):
    active=frame[frame.terminal_current<-.1].sort_values('time').copy()
    t=active.time.to_numpy();v=active.terminal_voltage.to_numpy();i=-active.terminal_current.to_numpy()
    if len(t)<100 or np.any(np.diff(t)<=0):raise ValueError('Insufficient or duplicate discharge time')
    cv=float(np.std(i)/np.mean(i))
    if cv>.1:raise ValueError('Not sufficiently constant current')
    if np.max(np.diff(t))>60:raise ValueError('Discharge sampling gap exceeds 60s')
    if v.max()-v.min()<.3:raise ValueError('Voltage span insufficient')
    q=cumulative_trapezoid(i,t,initial=0)/3600
    # Uniform 10 mV grid; average repeated voltages before interpolation.
    smooth=savgol_filter(v,21,3)
    reversals=float(np.mean(np.diff(smooth)>.001))
    if reversals>.1:raise ValueError('Voltage not sufficiently monotonic after smoothing')
    unique=pd.DataFrame(dict(v=smooth,q=q)).groupby('v',as_index=False).q.mean()
    vg=np.arange(unique.v.min()+.02,unique.v.max()-.02,.01)
    if len(vg)<25:raise ValueError('Too few voltage bins')
    qv=np.interp(vg,unique.v,unique.q)
    qv=savgol_filter(qv,11,3)
    ic=np.gradient(qv,vg)
    qg=np.linspace(q[0]+.02,q[-1]-.02,200)
    vq=savgol_filter(np.interp(qg,q,smooth),11,3)
    dv=np.gradient(vq,qg)
    return dict(current_cv=cv,voltage_reversal_fraction=reversals,integrated_ah=float(q[-1]),
                ica=[dict(voltage=float(a),dqdv=float(b)) for a,b in zip(vg,ic)],
                dva=[dict(capacity=float(a),dvdq=float(b)) for a,b in zip(qg,dv)])


def main():
    out=ROOT/'reports/research';out.mkdir(parents=True,exist_ok=True)
    data=table('reports/features.csv')
    samples=pd.concat([g.sort_values('cycle').iloc[np.unique(np.linspace(0,len(g)-1,min(3,len(g))).astype(int))] for _,g in data.groupby(['battery','phase'])])
    model=artifact('boosting/catboost.joblib')['model']
    x=samples[FEATURES]
    shap=np.asarray(model.get_feature_importance(Pool(x),type='ShapValues',thread_count=2))
    pred=np.asarray(model.predict(x))
    error=float(np.max(np.abs(shap[:,-1]+shap[:,:-1].sum(axis=1)-pred)))
    if error>.002:raise ValueError('SHAP reconstruction mismatch')
    rows=[]
    for j,f in enumerate(FEATURES):
        rows.append(dict(feature=f,mean_abs_shap=float(np.abs(shap[:,j]).mean()),
                         points=[dict(value=float(a),shap=float(b)) for a,b in zip(x[f],shap[:,j])]))
    report=dict(model='CatBoost',samples=len(x),batteries=int(samples.battery.nunique()),
                scope='Descriptive final-model SHAP; includes training data, not held-out accuracy or causal evidence.',
                sampling='Up to 3 evenly spaced observed cycles per battery and phase; all groups have equal sampling quota.',
                reconstruction_max_error=error,features=sorted(rows,key=lambda r:-r['mean_abs_shap']),
                model_sha256=sha(ROOT/'artifacts/boosting/catboost.joblib'),source_sha256=sha(ROOT/'reports/features.csv'))
    (out/'shap_summary.json').write_text(json.dumps(report,ensure_ascii=False),encoding='utf-8')
    pd.DataFrame([{'feature':r['feature'],'mean_abs_shap':r['mean_abs_shap']} for r in report['features']]).to_csv(out/'shap_importance.csv',index=False)
    results=[];rejected=[]
    for phase in ['primary','second_life']:
        subset=data[(data.battery=='SDU_01')&(data.phase==phase)].sort_values('cycle')
        for cycle in subset.cycle.iloc[np.unique(np.linspace(0,len(subset)-1,3).astype(int))]:
            try:results.append(dict(battery='SDU_01',phase=phase,cycle=int(cycle),**curves(cycle_measurements('SDU_01',int(cycle),phase))))
            except ValueError as e:rejected.append(dict(phase=phase,cycle=int(cycle),reason=str(e)))
    (out/'electrochemical_curves.json').write_text(json.dumps(dict(curves=results,rejected=rejected,
        method='Full discharge, integrate -I dt /3600; voltage Savitzky-Golay 21 points degree 3; ICA on 10mV grid smoothed 11 points; DVA on 200 capacity points smoothed 11 points.',
        scope='Exploratory full-discharge curves, NOT inputs to 120s predictor; no claim about chemical degradation mechanism.'),ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(shap_samples=len(x),shap_error=error,curves=len(results),rejected=rejected),ensure_ascii=True))

if __name__=='__main__':main()
