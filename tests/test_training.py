import io,json,base64,zipfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np,pandas as pd,joblib
from webapp.server import app,INFERENCE
from webapp.training import run
from battery_soh.features import FEATURES
ROOT=Path(__file__).resolve().parents[1]
class TrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data=pd.read_csv(ROOT/'reports/features.csv');pins=sorted(data.battery.unique())[:8]
        cls.data=data[data.battery.isin(pins)].groupby(['battery','phase'],group_keys=False).head(8)[['battery',*FEATURES,'soh_pct']]
        cls.raw=cls.data.to_csv(index=False).encode()
        cls.result=run(cls.raw,label_source='Measured reference capacity / nominal')
    def test_split_and_baseline(self):
        r=self.result
        self.assertFalse(set(r['train_batteries'])&set(r['test_batteries']))
        self.assertEqual(r['n_train']+r['n_test'],len(self.data))
        self.assertNotIn('soh_pct',r['features']);self.assertNotIn('battery',r['features'])
        mean=self.data[self.data.battery.isin(r['train_batteries'])].soh_pct.mean()
        pred=[x for x in r['predictions'] if x['model']=='Mean baseline']
        self.assertEqual(len(pred),r['n_test'])
        self.assertTrue(all(abs(x['predicted_soh']-mean)<1e-9 for x in pred))
    def test_bundle_preserves_train_only_scaling_and_label_source(self):
        z=zipfile.ZipFile(io.BytesIO(base64.b64decode(self.result['bundle_base64'])))
        meta=json.loads(z.read('results.json'))
        self.assertEqual(meta['label_source'],'Measured reference capacity / nominal')
        self.assertEqual(meta['configurations']['Random Forest']['n_estimators'],80)
        self.assertIn('scikit-learn',meta['versions'])
        ridge=joblib.load(io.BytesIO(z.read('ridge.joblib')))['model']
        train=self.data[self.data.battery.isin(self.result['train_batteries'])]
        np.testing.assert_allclose(ridge.steps[0][1].mean_,train[FEATURES].mean().to_numpy())
    def test_missing_target_and_too_few_groups(self):
        with self.assertRaises(ValueError):run(self.data.drop(columns='soh_pct').to_csv(index=False).encode())
        with self.assertRaises(ValueError):run(self.data[self.data.battery.isin(sorted(self.data.battery.unique())[:2])].to_csv(index=False).encode())
    def test_duplicate_and_nonfinite_are_rejected(self):
        with self.assertRaises(ValueError):run(pd.concat([self.data,self.data.iloc[[0]]]).to_csv(index=False).encode())
        bad=self.data.copy();bad.iloc[0,bad.columns.get_loc('voltage_mean')]=np.nan
        with self.assertRaises(ValueError):run(bad.to_csv(index=False).encode())
    def test_routes_and_busy_response(self):
        c=app.test_client()
        with INFERENCE:
            response=c.post('/api/training',data={'file':(io.BytesIO(self.raw),'data.csv'),'label_source':'test reference'})
        self.assertEqual(response.status_code,429)
        response=c.post('/api/training',data={'file':(io.BytesIO(self.raw),'data.csv'),'label_source':'test reference'})
        self.assertEqual(response.status_code,200,response.get_json())
        self.assertEqual(len(response.get_json()['scores']),3)
        with c.get('/api/download/training-template') as r:self.assertEqual(r.status_code,200)
    def test_benchmark_is_light_and_matches_audited_rows(self):
        c=app.test_client()
        with patch('webapp.server.evaluation_results',side_effect=AssertionError('Heavy predictions must not load')):
            for source in ['SDU','BMS']:
                response=c.get('/api/benchmarks?dataset='+source)
                self.assertEqual(response.status_code,200)
                expected=pd.read_csv(ROOT/('reports/thesis_audit/'+source.lower()+'_summary.csv'))
                self.assertEqual(len(response.get_json()['rows']),len(expected))
                for row in response.get_json()['rows']:
                    original=expected[expected.model==row['model']].iloc[0]
                    self.assertAlmostEqual(row['macro_mae'],original.macro_mae)
        self.assertEqual(c.get('/api/benchmarks?dataset=unknown').status_code,400)
