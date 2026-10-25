"""Verify the standalone web preserves model results and rejects invalid inputs."""
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from webapp.server import app
from webapp.data import table, artifact
from battery_soh.features import FEATURES,extract_window


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client=app.test_client()

    def test_html_is_a_real_web_document(self):
        response=self.client.get('/')
        html=response.get_data(as_text=True)
        self.assertEqual(response.status_code,200)
        self.assertIn('<title>Vincent D |',html)
        self.assertIn('property="og:title"',html)
        self.assertNotIn('streamlit',html.lower())
        for path in ['/static/app.js','/static/app.css','/assets/logo.png','/static/icons/grid.svg']:
            with self.client.get(path) as asset:
                self.assertEqual(asset.status_code,200,path)

    def test_read_pages_and_health(self):
        for path in ['/healthz','/_stcore/health','/api/overview','/api/trends','/api/explorer',
                     '/api/evaluation','/api/anomalies','/api/bms','/api/quality','/api/version']:
            with self.subTest(path=path):
                response=self.client.get(path)
                self.assertEqual(response.status_code,200,response.get_data(as_text=True)[:300])

    def test_forecast_matches_the_saved_models(self):
        frame=table('data/clean/sample_measurements.csv')
        frame=frame[(frame.battery=='SDU_01')&(frame.phase_code==0)&(frame.cycle==1)&(frame.time<=120)]
        features=pd.DataFrame([extract_window(frame,1)])[FEATURES]
        files={'Random Forest':'random_forest.joblib','Ridge-RF residual':'ridge_residual_forest.joblib',
               'CatBoost':'boosting/catboost.joblib','XGBoost':'boosting/xgboost.joblib'}
        for name,filename in files.items():
            expected=float(artifact(filename)['model'].predict(features)[0])
            response=self.client.post('/api/forecast',data={'sample':'1','model':name,'phase_code':'0'})
            self.assertEqual(response.status_code,200,response.json)
            actual=response.json['results'][0]['predicted_soh_pct']
            self.assertAlmostEqual(actual,expected,places=7)
            explanation=response.json['explanation']
            # Native XGBoost SHAP accumulates float32 values; allow 0.0001 SOH points.
            self.assertAlmostEqual(explanation['baseline']+sum(x['contribution'] for x in explanation['effects']),expected,delta=1e-4)

    def test_audit_never_loads_a_model(self):
        with patch('webapp.server.artifact',side_effect=AssertionError('audit called a model')):
            response=self.client.post('/api/audit',data={'sample':'1','phase_code':'0'})
        self.assertEqual(response.status_code,200,response.json)
        self.assertTrue(all(x['status']=='Hợp lệ' for x in response.json['checks']))

    def test_invalid_data_does_not_become_a_prediction(self):
        response=self.client.post('/api/forecast',data={'file':(io.BytesIO(b'hello,world\n1,2\n'),'bad.csv')},content_type='multipart/form-data')
        self.assertIn(response.status_code,[200,400])
        if response.status_code==200:
            self.assertTrue(all(r['status']!='Thành công' for r in response.json['results']))
        self.assertEqual(self.client.get('/api/explorer?battery=../../secret').status_code,400)
        self.assertEqual(self.client.get('/api/trends?phase=wrong').status_code,400)
        self.assertEqual(self.client.post('/api/forecast',data={'sample':'1','phase_code':'2'}).status_code,400)

    def test_cross_origin_submission_is_rejected(self):
        response=self.client.post('/api/forecast',data={'sample':'1'},headers={'Origin':'https://another-site.example'})
        self.assertEqual(response.status_code,403)

    def test_bms_keeps_derived_label_scope(self):
        response=self.client.post('/api/bms/predict',data={'sample':'1','model':'Random Forest'})
        self.assertEqual(response.status_code,200,response.json)
        self.assertTrue(np.isfinite(response.json['prediction']))
        invalid=self.client.post('/api/bms/predict',data={'file':(io.BytesIO(b'time_s,soc\n0,20\n'),'bms.csv')},content_type='multipart/form-data')
        self.assertEqual(invalid.status_code,400)
        self.assertIn('145 Ah',invalid.json['error'])

    def test_downloads_use_the_real_csv_schema(self):
        with self.client.get('/api/download/sample') as response:
            self.assertEqual(response.status_code,200)
            frame=pd.read_csv(io.BytesIO(response.data))
            self.assertTrue({'time','terminal_voltage','terminal_current','temperature','cycle','phase_code'}<=set(frame))
            self.assertLessEqual(frame.time.max(),120)

    def test_single_cycle_csv_uses_the_entered_cycle(self):
        frame=table('data/clean/sample_measurements.csv')
        frame=frame[(frame.battery=='SDU_01')&(frame.phase_code==0)&(frame.cycle==1)&(frame.time<=120)].drop(columns='cycle')
        response=self.client.post('/api/forecast',data={'cycle':'10','phase_code':'0','model':'Random Forest',
            'file':(io.BytesIO(frame.to_csv(index=False).encode()),'single.csv')},content_type='multipart/form-data')
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json['results'][0]['cycle'],10)
        self.assertEqual(response.json['results'][0]['status'],'Thành công')

    def test_demo_uses_an_unseen_battery(self):
        response=self.client.get('/api/demo')
        self.assertEqual(response.status_code,200,response.json)
        fitted=artifact('random_forest_demo.joblib')
        self.assertNotIn(response.json['battery'],fitted['batteries'])
        self.assertGreater(len(response.json['results']),0)


if __name__=='__main__':
    unittest.main()
