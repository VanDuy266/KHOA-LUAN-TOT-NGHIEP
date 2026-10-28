"""Build independent binary fault baseline from public CC-BY Zenodo v1 data only."""
from pathlib import Path
import sys,json,hashlib,subprocess,io
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import classification_report,confusion_matrix,balanced_accuracy_score,precision_score,recall_score,f1_score,accuracy_score
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from webapp.fault import snapshot_features,FEATURES


def main():
    archive=ROOT/'data/fault/raw/source.rar'
    assert hashlib.md5(archive.read_bytes()).hexdigest()=='190be964af39615428834747654e853f'
    base=ROOT/'data/fault/extracted/Data & Code';out=ROOT/'reports/fault';out.mkdir(parents=True,exist_ok=True)
    frames=[]
    for p in sorted((base/'Data').glob('*/*.csv'),key=lambda p:(int(p.parent.name),int(p.stem))):
        voltage=pd.read_csv(p);labels=pd.read_csv(base/'Label'/p.parent.name/p.name).to_numpy().ravel()
        f=snapshot_features(voltage);assert len(labels)==len(f) and set(labels)<={0,1,2,3,4}
        f['vehicle']=int(p.parent.name);f['snapshot']=int(p.stem);f['cell']=np.arange(1,15)
        f['source_label']=labels.astype(int);f['fault']=(labels!=0).astype(int);frames.append(f)
    data=pd.concat(frames,ignore_index=True);oof=np.zeros(len(data),dtype=int);folds=np.zeros(len(data),dtype=int);splits=[]
    for fold,(train,test) in enumerate(StratifiedGroupKFold(5,shuffle=True,random_state=42).split(data,data.fault,groups=data.vehicle),1):
        assert set(data.vehicle.iloc[train]).isdisjoint(data.vehicle.iloc[test])
        model=RandomForestClassifier(n_estimators=120,max_depth=12,min_samples_leaf=5,class_weight='balanced_subsample',random_state=42,n_jobs=2)
        model.fit(data.iloc[train][FEATURES],data.fault.iloc[train]);oof[test]=model.predict(data.iloc[test][FEATURES]);folds[test]=fold
        splits.append(dict(fold=fold,train_vehicles=sorted(data.vehicle.iloc[train].unique().tolist()),test_vehicles=sorted(data.vehicle.iloc[test].unique().tolist())))
        print('Fault fold',fold,'complete',flush=True)
    data['prediction']=oof;data['fold']=folds
    data.to_csv(out/'features_predictions.csv.gz',index=False,compression='gzip')
    data[['vehicle','snapshot','cell','source_label','fault','prediction','fold']].to_csv(out/'oof_predictions.csv.gz',index=False,compression='gzip')
    def metrics(pred):return dict(accuracy=accuracy_score(data.fault,pred),balanced_accuracy=balanced_accuracy_score(data.fault,pred),precision=precision_score(data.fault,pred,zero_division=0),recall=recall_score(data.fault,pred,zero_division=0),f1=f1_score(data.fault,pred,zero_division=0),confusion_matrix=confusion_matrix(data.fault,pred,labels=[0,1]).tolist())
    result=dict(source='https://zenodo.org/records/18505707',doi='10.5281/zenodo.18505707',license='CC BY 4.0',citation='J. Li, Y. Che, S. Onori, W. Li, X. Hu, Decoupling battery faults from sparse voltage snapshots via cross-modal topology',archive_md5=hashlib.md5(archive.read_bytes()).hexdigest(),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),vehicles=int(data.vehicle.nunique()),snapshots=len(frames),samples=len(data),source_claimed_samples=47968,source_count_mismatch='Downloaded CSVs contain 47,698 cell-snapshot samples; README states 47,968. Report actual count without silently changing source.',source_label_counts={str(k):int(v) for k,v in data.source_label.value_counts().items()},target='0 = source class 0; 1 = any source fault class 1..4; no unsupported mapping of individual fault types',method='Random Forest binary baseline; 9 per-cell voltage/residual descriptors, fixed parameters; 5-fold StratifiedGroupKFold by vehicle, seed 42; no tuning',metrics=metrics(oof),majority_baseline=metrics(np.zeros(len(data),dtype=int)),limits=['Processed voltage snapshots, not raw complete vehicle histories.','No SOC, capacity SOH, charge counts or time-to-failure labels.','Model prediction is a fault signal for this source domain, not confirmed physical failure or safety certification.','Does not apply to existing BAIC max/min BMS CSV schema.','Individual source class-to-fault-type mapping not confirmed, so binary labels only.'])
    (out/'summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),'utf-8');(out/'splits.json').write_text(json.dumps(splits,indent=2),'utf-8')
    model.fit(data[FEATURES],data.fault);art=ROOT/'artifacts/fault';art.mkdir(parents=True,exist_ok=True)
    joblib.dump(dict(model=model,features=FEATURES,dataset='Zenodo 18505707 v1 voltage snapshots',training_min=data[FEATURES].min().to_dict(),training_max=data[FEATURES].max().to_dict()),art/'random_forest.joblib',compress=3)
    # Small demonstration set covers true positives, false negatives, false positives and true negatives where available.
    cases=[]
    for truth,pred in [(0,0),(1,1),(1,0),(0,1)]:
        for (vehicle,snapshot),g in data[(data.fault==truth)&(data.prediction==pred)].groupby(['vehicle','snapshot']):
            cases.append(dict(id=f'{vehicle}-{snapshot}',vehicle=int(vehicle),snapshot=int(snapshot),fold=int(g.fold.iloc[0])))
            if len([c for c in cases if c.get('bucket')==[truth,pred]])>=2:break
            cases[-1]['bucket']=[truth,pred]
            if sum(c.get('bucket')==[truth,pred] for c in cases)>=2:break
    unique={c['id']:c for c in cases};examples=[]
    for c in unique.values():
        p=base/'Data'/str(c['vehicle'])/(str(c['snapshot'])+'.csv');v=pd.read_csv(p)
        g=data[(data.vehicle==c['vehicle'])&(data.snapshot==c['snapshot'])]
        examples.append(dict(**c,columns=v.columns.tolist(),voltage=v.to_numpy().tolist(),cells=g[['cell','fault','prediction']].to_dict('records')))
    processed=ROOT/'data/fault/processed';processed.mkdir(exist_ok=True)
    (processed/'examples.json').write_text(json.dumps(examples),'utf-8')
    print(json.dumps(result['metrics']),flush=True)

if __name__=='__main__':main()
