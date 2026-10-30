"""Build lightweight UI summaries from audited metrics and saved timing logs."""
from pathlib import Path
import json,hashlib,sys,io,pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from webapp.benchmark_sources import source_hash,source_text
def read_frame(relative):
    return pd.read_csv(io.StringIO(source_text(ROOT/relative)))

def main():
    used=['reports/thesis_audit/sdu_summary.csv','reports/thesis_audit/bms_summary.csv','reports/timings.csv','reports/boosting/timings.csv','reports/hybrid_metadata.json','reports/bms/timings.csv']
    frames={'SDU':pd.concat([read_frame('reports/timings.csv').query('model != "Ridge-RF residual"'),read_frame('reports/boosting/timings.csv'),pd.DataFrame([dict(r,model='Ridge-RF residual') for r in json.loads(source_text(ROOT/'reports/hybrid_metadata.json'))['timings']])],ignore_index=True),'BMS':read_frame('reports/bms/timings.csv')}
    result={}
    for source,timings in frames.items():
        rows=read_frame('reports/thesis_audit/'+source.lower()+'_summary.csv')
        metrics=[]
        for r in rows.to_dict('records'):
            part=timings[timings.model==r['model']];valid=part[part.predict_seconds.notna() & part.n_test.gt(0)]
            r.update(fit_seconds_mean=float(part.fit_seconds.mean()),predict_ms_per_sample=None if valid.empty else float(1000*valid.predict_seconds.sum()/valid.n_test.sum()),timed_folds=len(valid),total_timing_folds=len(part))
            metrics.append(r)
        result[source]=dict(dataset=source,rows=metrics,reference='Dung lượng xả / 2,4 Ah' if source=='SDU' else 'Dung lượng vận hành suy ra từ dòng điện/SOC /145 Ah')
    result['hash_method']='SHA256 of UTF-8 text with LF newlines; CSV gzip packaging transparent'
    result['source_hashes']={p:source_hash(ROOT/p) for p in used}
    (ROOT/'reports/thesis_audit/ui_benchmarks.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    print('Built audited benchmark summaries')
if __name__=='__main__':main()
