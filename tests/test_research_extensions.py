import json,unittest
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.metrics import mean_absolute_error,root_mean_squared_error,r2_score
from webapp.server import app
ROOT=Path(__file__).resolve().parents[1]
class ResearchExtensionTests(unittest.TestCase):
    def test_shap_sampling_and_reconstruction(self):
        r=json.loads((ROOT/'reports/research/shap_summary.json').read_text(encoding='utf-8'))
        self.assertEqual(r['samples'],516)
        self.assertEqual(r['batteries'],86)
        self.assertLess(r['reconstruction_max_error'],.002)
        for feature in r['features']:
            self.assertEqual(len(feature['points']),516)
            self.assertAlmostEqual(feature['mean_abs_shap'],np.mean([abs(x['shap']) for x in feature['points']]))
    def test_full_discharge_curves_are_finite_and_ordered(self):
        r=json.loads((ROOT/'reports/research/electrochemical_curves.json').read_text(encoding='utf-8'))
        self.assertEqual(len(r['curves']),6)
        for c in r['curves']:
            self.assertLessEqual(c['current_cv'],.1)
            for values,x,y in [(c['ica'],'voltage','dqdv'),(c['dva'],'capacity','dvdq')]:
                self.assertTrue(np.isfinite([[v[x],v[y]] for v in values]).all())
                self.assertTrue((np.diff([v[x] for v in values])>0).all())
    def test_nasa_split_and_metric_reconstruction(self):
        d=json.loads((ROOT/'reports/research/nasa_transfer.json').read_text(encoding='utf-8'))
        self.assertEqual(d['retained'],636)
        self.assertEqual(d['excluded'],0)
        for split in d['splits']:
            self.assertNotIn(split['test_cell'],split['train_nasa_cells'])
            self.assertEqual(len(split['train_nasa_cells']),3)
        pred=pd.read_csv(ROOT/'reports/research/nasa_predictions.csv')
        for row in d['summary']:
            g=pred[pred.experiment==row['experiment']]
            self.assertEqual(len(g),636)
            self.assertFalse(g.duplicated(['battery','cycle']).any())
            by=[p for _,p in g.groupby('battery')]
            self.assertEqual(len(by),4)
            self.assertAlmostEqual(row['mae'],np.mean([mean_absolute_error(p.actual_soh,p.predicted_soh) for p in by]))
            self.assertAlmostEqual(row['rmse'],np.mean([root_mean_squared_error(p.actual_soh,p.predicted_soh) for p in by]))
            self.assertAlmostEqual(row['r2'],np.mean([r2_score(p.actual_soh,p.predicted_soh) for p in by]))
    def test_research_routes_are_whitelisted(self):
        c=app.test_client()
        for section in ['shap','curves','transfer']:
            self.assertEqual(c.get('/api/research?section='+section).status_code,200)
        self.assertEqual(c.get('/api/research?section=../server.py').status_code,400)
        for kind in ['shap','nasa','predictions','protocol','curves']:
            with c.get('/api/download/research?kind='+kind) as r:self.assertEqual(r.status_code,200)
