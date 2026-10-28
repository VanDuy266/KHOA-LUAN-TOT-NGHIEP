"""NASA external evaluation, fixed SDU models and leave-one-NASA-cell-out experiments."""
from pathlib import Path
import sys,json,hashlib
import numpy as np,pandas as pd
from scipy.io import loadmat
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error,root_mean_squared_error,r2_score
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'app')]
from webapp.data import artifact,table,MODELS
from battery_soh.features import FEATURES,extract_window


def main():
    raw=ROOT/'data/external/nasa';out=ROOT/'reports/research';out.mkdir(exist_ok=True,parents=True)
    rows=[];excluded=[];counts={};checksums={}
    for pin in ['B0005','B0006','B0007','B0018']:
        path=raw/(pin+'.mat')
        with path.open('rb') as f:checksums[path.name]=hashlib.file_digest(f,'sha256').hexdigest()
        cycles=loadmat(path,simplify_cells=True)[pin]['cycle'];number=0
        for op in cycles:
            if op['type']!='discharge':continue
            number+=1;d=op['data']
            frame=pd.DataFrame(dict(time=d['Time'],terminal_voltage=d['Voltage_measured'],terminal_current=d['Current_measured'],temperature=d['Temperature_measured']))
            try:
                features=extract_window(frame,number,phase_code=0)
                capacity=float(d['Capacity'])
                if not np.isfinite(capacity) or capacity<=0:raise ValueError('Invalid reference capacity')
                rows.append(dict(battery=pin,phase='primary',**features,capacity_ah=capacity,soh_pct=capacity/2*100))
            except ValueError as e:excluded.append(dict(battery=pin,cycle=number,reason=str(e)))
        counts[pin]=number
    nasa=pd.DataFrame(rows);nasa.to_csv(out/'nasa_features.csv',index=False)
    pd.DataFrame(excluded,columns=['battery','cycle','reason']).to_csv(out/'nasa_excluded.csv',index=False)
    predictions=[]
    def save(name,part,pred):
        predictions.extend(dict(experiment=name,battery=r.battery,cycle=int(r.cycle),actual_soh=float(r.soh_pct),predicted_soh=float(p)) for r,p in zip(part.itertuples(),pred))
    for name,path in MODELS.items():
        model=artifact(path)['model'];save('SDU → NASA · '+name,nasa,model.predict(nasa[FEATURES]))
    # Hyperparameters fixed to existing RF, not selected by NASA test outcomes.
    template=artifact('random_forest.joblib')['model']
    sdu=table('reports/features.csv').copy();sdu['nominal_ah']=2.4
    nasa['nominal_ah']=2.
    splits=[]
    for pin in nasa.battery.unique():
        train=nasa[nasa.battery!=pin];test=nasa[nasa.battery==pin]
        assert set(train.battery).isdisjoint(test.battery)
        splits.append(dict(test_cell=pin,train_nasa_cells=sorted(train.battery.unique()),test_samples=len(test),train_nasa_samples=len(train),pooled_sdu_cells=int(sdu.battery.nunique())))
        model=clone(template);model.n_jobs=2;model.fit(train[FEATURES],train.soh_pct)
        save('NASA → NASA · giữ riêng cell',test,model.predict(test[FEATURES]))
        mixed=pd.concat([sdu,train],ignore_index=True)
        model=clone(template);model.n_jobs=2;model.fit(mixed[FEATURES+['nominal_ah']],mixed.soh_pct)
        save('SDU + NASA → cell NASA giữ riêng',test,model.predict(test[FEATURES+['nominal_ah']]))
        print('Evaluated held-out',pin,flush=True)
    pred=pd.DataFrame(predictions);pred.to_csv(out/'nasa_predictions.csv',index=False)
    per=[]
    for (name,pin),g in pred.groupby(['experiment','battery']):
        per.append(dict(experiment=name,battery=pin,samples=len(g),mae=mean_absolute_error(g.actual_soh,g.predicted_soh),rmse=root_mean_squared_error(g.actual_soh,g.predicted_soh),r2=r2_score(g.actual_soh,g.predicted_soh)))
    by=pd.DataFrame(per);by.to_csv(out/'nasa_by_battery.csv',index=False)
    summary=by.groupby('experiment',sort=False).agg(cells=('battery','nunique'),samples=('samples','sum'),mae=('mae','mean'),rmse=('rmse','mean'),r2=('r2','mean')).reset_index()
    for name,path in MODELS.items():
        with (ROOT/'artifacts'/path).open('rb') as f:checksums['model/'+name]=hashlib.file_digest(f,'sha256').hexdigest()
    with (ROOT/'reports/features.csv').open('rb') as f:checksums['sdu_features']=hashlib.file_digest(f,'sha256').hexdigest()
    report=dict(source_page='https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/',
      download='https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip',
      citation='B. Saha and K. Goebel (2007), Battery Data Set, NASA Ames Prognostics Data Repository.',
      archive_sha256='82302a7db4fc1b34e0b6676326610438d43b816bdf11a69d1d012a464ef2f92e',
      raw_sha256=checksums,splits=splits,rf_parameters=template.get_params(),original_discharge_counts=counts,retained=len(nasa),excluded=len(excluded),
      protocol='Fixed 120s features and phase_code=0 convention; SOH=source Capacity/2Ah*100. Zero-shot models unchanged. NASA and pooled RF leave one complete NASA cell out; no tuning on test labels. Pooled includes nominal capacity, but is NOT unseen-source validation.',
      limitation='Four laboratory cells only; different discharge cutoffs and reference-capacity protocol from SDU. Cycle ordinal and phase convention are not domain invariant. Source README does not establish exact chemistry equivalence. No claim of universal model, safety or fault prediction.',
      summary=summary.to_dict('records'))
    (out/'nasa_transfer.json').write_text(json.dumps(report,ensure_ascii=False),encoding='utf-8')
    print(summary.to_string(index=False));print('retained',len(nasa),'excluded',len(excluded))

if __name__=='__main__':main()
