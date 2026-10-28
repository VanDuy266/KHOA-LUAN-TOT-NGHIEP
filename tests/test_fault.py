import unittest,io
import numpy as np
import pandas as pd
from webapp.fault import snapshot_features,FEATURES
from webapp.server import app
from webapp.data import metadata,table

class FaultTests(unittest.TestCase):
    def test_features_use_voltage_only_and_shape(self):
        f=pd.DataFrame(np.full((50,14),4000.))
        x=snapshot_features(f);self.assertEqual(x.shape,(14,9))
        self.assertEqual(x.residual_mean.sum(),0)
        for bad in [f.iloc[:-1],f.assign(label=0)]:
            with self.assertRaises(ValueError):snapshot_features(bad)
    def test_examples_are_true_oof(self):
        c=app.test_client();overview=c.get('/api/fault').json
        self.assertEqual(overview['summary']['vehicles'],99)
        for example in metadata('data/fault/processed/examples.json'):
            split=next(s for s in metadata('reports/fault/splits.json') if s['fold']==example['fold'])
            self.assertIn(example['vehicle'],split['test_vehicles'])
            self.assertNotIn(example['vehicle'],split['train_vehicles'])
            r=c.post('/api/fault/predict',data={'sample_id':example['id']})
            self.assertEqual(r.status_code,200,r.json)
            self.assertEqual(len(r.json['cells']),14)
    def test_uploaded_snapshot_and_baic_rejected(self):
        c=app.test_client();e=metadata('data/fault/processed/examples.json')[0]
        f=pd.DataFrame(e['voltage'],columns=e['columns'])
        r=c.post('/api/fault/predict',data={'file':(io.BytesIO(f.to_csv(index=False).encode()),'voltage.csv')})
        self.assertEqual(r.status_code,200,r.json)
        self.assertTrue(all(x['reference'] is None for x in r.json['cells']))
        r=c.post('/api/fault/predict',data={'file':(io.BytesIO(b'max_cell_voltage,min_cell_voltage\n4.1,4.0'),'baic.csv')})
        self.assertEqual(r.status_code,400)
    def test_saved_predictions_cover_once_per_cell_and_group(self):
        d=table('reports/fault/oof_predictions.csv.gz')
        self.assertFalse(d.duplicated(['vehicle','snapshot','cell']).any())
        self.assertEqual(d.groupby('vehicle').fold.nunique().max(),1)
        self.assertEqual(len(d),47698)
    def test_bms_charge_count_and_lifetime_unknown(self):
        c=app.test_client();r=c.post('/api/health',data={'kind':'bms','vehicle':'BAIC_01'})
        self.assertEqual(r.status_code,200,r.json)
        data=table('reports/bms/features.csv');expected=data[data.vehicle=='BAIC_01'].session.nunique()
        self.assertEqual(r.json['result']['charge_sessions'],expected)
        self.assertIsNone(r.json['result']['lifetime_charge_count'])
        short=c.post('/api/health',data={'kind':'bms','vehicle':'BAIC_01','cutoff':'6'})
        self.assertEqual(short.status_code,200,short.json)
        self.assertLess(short.json['result']['charge_sessions'],expected)

if __name__=='__main__':unittest.main()
