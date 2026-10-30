"""Build lightweight UI summaries from audited metrics and saved timing logs."""
from pathlib import Path
import json,hashlib,pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parents[1]
def main():
    used=['reports/thesis_audit/sdu_summary.csv','reports/thesis_audit/bms_summary.csv','reports/timings.csv','reports/boosting/timings.csv','reports/hybrid_metadata.json','reports/bms/timings.csv']
    frames={'SDU':pd.concat([pd.read_csv(ROOT/'reports/timings.csv').query('model != "Ridge-RF residual"'),pd.read_csv(ROOT/'reports/boosting/timings.csv'),pd.DataFrame([dict(r,model='Ridge-RF residual') for r in json.loads((ROOT/'reports/hybrid_metadata.json').read_text())['timings']])],ignore_index=True),'BMS':pd.read_csv(ROOT/'reports/bms/timings.csv')}
    result={}
    for source,timings in frames.items():
        rows=pd.read_csv(ROOT/('reports/thesis_audit/'+source.lower()+'_summary.csv'))
        metrics=[]
        for r in rows.to_dict('records'):
            part=timings[timings.model==r['model']];valid=part[part.predict_seconds.notna() & part.n_test.gt(0)]
            r.update(fit_seconds_mean=float(part.fit_seconds.mean()),predict_ms_per_sample=None if valid.empty else float(1000*valid.predict_seconds.sum()/valid.n_test.sum()),timed_folds=len(valid),total_timing_folds=len(part))
            metrics.append(r)
        result[source]=dict(dataset=source,rows=metrics,reference='Dung lượng xả / 2,4 Ah' if source=='SDU' else 'Dung lượng vận hành suy ra từ dòng điện/SOC /145 Ah')
    result['source_hashes']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in used}
    (ROOT/'reports/thesis_audit/ui_benchmarks.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    print('Built audited benchmark summaries')
if __name__=='__main__':main()
