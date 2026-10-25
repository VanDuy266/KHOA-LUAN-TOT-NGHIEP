"""Evaluate published CatBoost/XGBoost libraries on unchanged SDU battery folds."""
import os
os.environ.setdefault('OMP_NUM_THREADS','2')
from pathlib import Path
import sys,json,time,hashlib
from collections import Counter
import numpy as np
import pandas as pd
import joblib
import catboost,xgboost
from catboost import CatBoostRegressor
from xgboost import XGBRegressor
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_absolute_error,root_mean_squared_error,r2_score
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from battery_soh.features import FEATURES
CANDIDATES={'CatBoost':[dict(depth=d,l2_leaf_reg=5) for d in (4,6,8)],
            'XGBoost':[dict(max_depth=d,min_child_weight=5,reg_lambda=5) for d in (3,5,7)]}

def build(name,params,trees,early=False):
    if name=='CatBoost':
        return CatBoostRegressor(**params,iterations=trees,learning_rate=.04,loss_function='RMSE',random_seed=42,thread_count=2,verbose=False,allow_writing_files=False)
    return XGBRegressor(**params,n_estimators=trees,learning_rate=.04,objective='reg:squarederror',eval_metric='rmse',tree_method='hist',subsample=1,colsample_bytree=1,n_jobs=2,random_state=42,**({'early_stopping_rounds':60} if early else {}))

def macro_mae(data,pred):
    frame=pd.DataFrame(dict(battery=data.battery.to_numpy(),actual=data.soh_pct.to_numpy(),prediction=pred))
    return float(np.mean([mean_absolute_error(g.actual,g.prediction) for _,g in frame.groupby('battery')]))

def main():
    out=ROOT/'reports/boosting';out.mkdir(parents=True,exist_ok=True)
    art=ROOT/'artifacts/boosting';art.mkdir(parents=True,exist_ok=True)
    data=pd.read_csv(ROOT/'reports/features.csv')
    folds=data.battery.map(pd.read_csv(ROOT/'reports/split_assignments.csv').set_index('battery').test_fold)
    assert folds.notna().all()
    predictions=[];scores=[];trials=[];timings=[];splits=[];selected={name:[] for name in CANDIDATES}
    for fold in sorted(folds.unique()):
        train=data[folds!=fold].reset_index(drop=True);test=data[folds==fold].reset_index(drop=True)
        ti,vi=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=42+int(fold)).split(train,groups=train.battery))
        inner=train.iloc[ti];valid=train.iloc[vi]
        assert set(inner.battery).isdisjoint(valid.battery) and set(train.battery).isdisjoint(test.battery)
        splits.append(dict(fold=int(fold),fit_batteries=sorted(inner.battery.unique()),validation_batteries=sorted(valid.battery.unique()),test_batteries=sorted(test.battery.unique())))
        for name,candidates in CANDIDATES.items():
            start=time.perf_counter();options=[]
            for candidate,params in enumerate(candidates):
                fitted=build(name,params,1000,early=True)
                if name=='CatBoost':
                    fitted.fit(inner[FEATURES],inner.soh_pct,eval_set=(valid[FEATURES],valid.soh_pct),early_stopping_rounds=60,use_best_model=True)
                    trees=int(fitted.get_best_iteration()+1)
                else:
                    fitted.fit(inner[FEATURES],inner.soh_pct,eval_set=[(valid[FEATURES],valid.soh_pct)],verbose=False)
                    trees=int(fitted.best_iteration+1)
                prediction=fitted.predict(valid[FEATURES]);score=macro_mae(valid,prediction)
                options.append((score,candidate,params,max(1,trees)))
                trials.append(dict(model=name,fold=int(fold),candidate=candidate,validation_macro_mae=score,trees=trees,parameters=json.dumps(params,sort_keys=True)))
                print(f'{name} fold {fold} candidate {candidate}: val macro MAE={score:.4f}, trees={trees}',flush=True)
            selection_seconds=time.perf_counter()-start
            _,candidate,params,trees=min(options,key=lambda row:(row[0],row[1]))
            selected[name].append(dict(parameters=params,trees=trees))
            fitted=build(name,params,trees)
            start=time.perf_counter();fitted.fit(train[FEATURES],train.soh_pct);fit_seconds=time.perf_counter()-start
            start=time.perf_counter();prediction=fitted.predict(test[FEATURES]);predict_seconds=time.perf_counter()-start
            part=test[['battery','phase','cycle','soh_pct']].rename(columns={'soh_pct':'actual_soh'}).copy()
            part['predicted_soh']=prediction;part['fold']=int(fold);part['model']=name;predictions.append(part)
            for battery,group in part.groupby('battery'):
                scores.append(dict(model=name,fold=int(fold),held_out_battery=battery,n_test=len(group),mae=mean_absolute_error(group.actual_soh,group.predicted_soh),rmse=root_mean_squared_error(group.actual_soh,group.predicted_soh),r2=r2_score(group.actual_soh,group.predicted_soh)))
            timings.append(dict(model=name,fold=int(fold),fit_seconds=fit_seconds,predict_seconds=predict_seconds,selection_seconds=selection_seconds,n_train=len(train),n_test=len(test),selected_trees=trees,candidate=candidate))
            print(f'{name} fold {fold} evaluated on held-out batteries',flush=True)
    pred=pd.concat(predictions,ignore_index=True);by=pd.DataFrame(scores)
    pred.to_csv(out/'predictions.csv',index=False);by.to_csv(out/'metrics_by_battery.csv',index=False)
    summary=by.groupby('model')[['mae','rmse','r2']].mean().reset_index();summary.to_csv(out/'metrics_summary.csv',index=False)
    pd.DataFrame(trials).to_csv(out/'validation_trials.csv',index=False);pd.DataFrame(timings).to_csv(out/'timings.csv',index=False)
    (out/'splits.json').write_text(json.dumps(splits,indent=2),encoding='utf-8')
    final_choices={}
    for name,choices in selected.items():
        keys=[json.dumps(c['parameters'],sort_keys=True) for c in choices]
        key=Counter(keys).most_common(1)[0][0];params=json.loads(key)
        trees=int(np.median([c['trees'] for c in choices if c['parameters']==params]))
        fitted=build(name,params,trees);fitted.fit(data[FEATURES],data.soh_pct)
        joblib.dump(dict(model=fitted,features=FEATURES,dataset='SDU',nominal_capacity_ah=2.4,window_seconds=120,batteries=sorted(data.battery.unique()),training_min=data[FEATURES].min().to_dict(),training_max=data[FEATURES].max().to_dict()),art/(name.lower()+'.joblib'))
        final_choices[name]=dict(parameters=params,trees=trees)
    metadata=dict(methods=list(CANDIDATES),candidates=CANDIDATES,final_choices=final_choices,catboost_version=catboost.__version__,xgboost_version=xgboost.__version__,data_sha256=hashlib.sha256((ROOT/'reports/features.csv').read_bytes()).hexdigest(),
        protocol='Same outer physical-battery folds; one group-held-out inner validation; best iteration via validation RMSE then candidate via validation macro MAE; refit full outer train before one test prediction; no test-driven tuning',
        caveat='Existing baselines use fixed parameters; new methods have a small validation search budget. Differences include both algorithm and tuning budget; no claim of universal superiority.',
        final_refit='Most frequent parameters selected by inner validation across folds; median tree count among matching selections; never selected by outer test MAE',
        sources={'CatBoost':'https://proceedings.neurips.cc/paper/2018/hash/14491b756b3a51daac41c24863285549-Abstract.html','XGBoost':'https://arxiv.org/abs/1603.02754'})
    (out/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(summary.to_string(index=False),flush=True);print('BOOSTING EXPERIMENT COMPLETE',flush=True)
if __name__=='__main__': main()
