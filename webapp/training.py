"""Small, explicit group-holdout experiment; never changes deployed models."""
import io,json,zipfile,hashlib,time,base64
import numpy as np,pandas as pd,joblib
import sklearn
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.dummy import DummyRegressor
from sklearn.metrics import mean_absolute_error,root_mean_squared_error,r2_score
from battery_soh.features import FEATURES


def run(raw,label_source="Không cung cấp"):
    required=[*FEATURES,'battery','soh_pct']
    data=pd.read_csv(io.BytesIO(raw),nrows=5001,usecols=lambda c:c in required)
    missing=set(required)-set(data)
    if missing:raise ValueError('Thiếu cột: '+', '.join(sorted(missing)))
    if not 40<=len(data)<=5000:raise ValueError('Huấn luyện thử cần 40–5.000 dòng đặc trưng có nhãn.')
    if data.battery.isna().any() or data.battery.astype(str).str.strip().eq('').any():raise ValueError('Mỗi dòng cần mã pin hợp lệ.')
    data['battery']=data.battery.astype(str).str.strip()
    if not 4<=data.battery.nunique()<=200:raise ValueError('Cần 4–200 pin độc lập, mỗi pin ít nhất 5 mẫu.')
    if data.groupby('battery').size().min()<5:raise ValueError('Mỗi pin cần ít nhất 5 mẫu.')
    numeric=data[FEATURES+['soh_pct']].apply(pd.to_numeric,errors='raise')
    if not np.isfinite(numeric.to_numpy()).all():raise ValueError('Đặc trưng và nhãn phải hữu hạn, không được thiếu.')
    data[FEATURES+['soh_pct']]=numeric
    if not data.soh_pct.between(0,130).all():raise ValueError('Nhãn SOH cần trong 0–130%.')
    if not data.phase_code.isin([0,1]).all() or (data.cycle<1).any() or (data.cycle%1!=0).any():raise ValueError('Kiểm tra phase_code 0/1 và chu kỳ nguyên dương.')
    if data.duplicated(['battery','phase_code','cycle']).any():raise ValueError('Trùng mã pin/giai đoạn/chu kỳ.')
    ti,vi=next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=42).split(data,groups=data.battery))
    train=data.iloc[ti];test=data.iloc[vi]
    if set(train.battery)&set(test.battery):raise ValueError('Không tách được nhóm pin.')
    if len(train)<20 or len(test)<5:raise ValueError('Chưa đủ mẫu cho tập học/kiểm thử.')
    models={'Mean baseline':DummyRegressor(strategy='mean'),'Ridge':make_pipeline(StandardScaler(),Ridge(alpha=1.)),
            'Random Forest':RandomForestRegressor(n_estimators=80,max_depth=10,min_samples_leaf=3,n_jobs=1,random_state=42)}
    scores=[];predictions=[];fitted={}
    for name,model in models.items():
        start=time.perf_counter();model.fit(train[FEATURES],train.soh_pct);fit_seconds=time.perf_counter()-start
        start=time.perf_counter();prediction=model.predict(test[FEATURES]);predict_seconds=time.perf_counter()-start
        per=[]
        for pin in sorted(test.battery.unique()):
            mask=test.battery.eq(pin).to_numpy();actual=test.soh_pct.to_numpy()[mask];p=prediction[mask]
            per.append(dict(battery=pin,mae=float(mean_absolute_error(actual,p)),rmse=float(root_mean_squared_error(actual,p)),r2=float(r2_score(actual,p)) if np.ptp(actual)>1e-10 else None))
        valid_r2=[r['r2'] for r in per if r['r2'] is not None]
        scores.append(dict(model=name,macro_mae=float(np.mean([r['mae'] for r in per])),macro_rmse=float(np.mean([r['rmse'] for r in per])),macro_r2=float(np.mean(valid_r2)) if valid_r2 else None,
                           fit_seconds=fit_seconds,predict_ms_per_sample=1000*predict_seconds/len(test),by_battery=per))
        predictions.extend(dict(model=name,battery=str(r.battery),phase_code=int(r.phase_code),cycle=int(r.cycle),actual_soh=float(r.soh_pct),predicted_soh=float(p)) for r,p in zip(test.itertuples(),prediction))
        fitted[name]=model
    report=dict(method='Group holdout 25%, seed=42; fixed configurations; no test-driven tuning.',
                source_sha256=hashlib.sha256(raw).hexdigest(),label_source=label_source,features=FEATURES,train_batteries=sorted(train.battery.unique()),test_batteries=sorted(test.battery.unique()),
                n_train=len(train),n_test=len(test),scores=scores,predictions=predictions,
                configurations={'Mean baseline':{'strategy':'mean'},'Ridge':{'alpha':1.,'scaling':'StandardScaler fit on training rows only'},'Random Forest':{'n_estimators':80,'max_depth':10,'min_samples_leaf':3,'n_jobs':1,'random_state':42}},
                versions={'scikit-learn':sklearn.__version__,'numpy':np.__version__,'pandas':pd.__version__},
                scope='Single group holdout on user-provided features and SOH labels; not five-fold thesis results or proof of cross-source performance.')
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('results.json',json.dumps(report,ensure_ascii=False))
        z.writestr('held_out_predictions.csv',pd.DataFrame(predictions).to_csv(index=False))
        for name,model in fitted.items():
            binary=io.BytesIO();joblib.dump(dict(model=model,features=FEATURES,train_batteries=report['train_batteries'],test_batteries=report['test_batteries'],source_sha256=report['source_sha256']),binary,compress=3)
            z.writestr(name.lower().replace(' ','_')+'.joblib',binary.getvalue())
    return dict(**report,bundle_base64=base64.b64encode(archive.getvalue()).decode('ascii'))
