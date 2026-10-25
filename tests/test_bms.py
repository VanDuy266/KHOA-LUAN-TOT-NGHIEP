"""Checks for feature/label separation in the field-derived BMS experiment."""
import sys, unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from battery_soh.bms import FEATURES, charging_features, tail_capacity

class FieldBMSChecks(unittest.TestCase):
    def sample(self):
        t=np.arange(0,2401,8,dtype=float)
        return pd.DataFrame(dict(time_s=t,soc=20+t*52.2/3600/145*100,
            pack_voltage=330+t/240,charge_current=np.full(len(t),-52.2),
            max_cell_voltage=3.7+t/21600,min_cell_voltage=3.68+t/21600,
            max_temperature=np.full(len(t),30.0),min_temperature=np.full(len(t),28.0)))
    def test_tail_reference_uses_actual_elapsed_time(self):
        self.assertAlmostEqual(tail_capacity(self.sample()),145.0,places=9)
    def test_reference_does_not_use_first_window(self):
        frame=self.sample();expected=tail_capacity(frame)
        frame.loc[frame.time_s<=120,'charge_current']=-200
        self.assertEqual(tail_capacity(frame),expected)
    def test_features_do_not_see_future_or_capacity_columns(self):
        frame=self.sample();expected=charging_features(frame)
        frame.loc[frame.time_s>120,['pack_voltage','charge_current']]=999
        frame['available_capacity']=999;frame['reference_soh_pct']=999
        self.assertEqual(charging_features(frame),expected)
        self.assertEqual(list(expected),FEATURES)
    def test_short_soc_span_cannot_create_reference(self):
        frame=self.sample();frame['soc']=50+frame.time_s*.001
        with self.assertRaises(ValueError): tail_capacity(frame)
    def test_short_window_is_rejected(self):
        with self.assertRaises(ValueError): charging_features(self.sample().iloc[:5])
ROOT = Path(__file__).resolve().parents[1]

@unittest.skipUnless((ROOT/'reports/bms/dataset_summary.json').exists(), 'Build BMS results first')
class SavedBMSChecks(unittest.TestCase):
    def test_held_out_predictions_and_metrics(self):
        import json
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        info=json.loads((ROOT/'reports/bms/dataset_summary.json').read_text(encoding='utf-8'))
        features=pd.read_csv(ROOT/'reports/bms/features.csv')
        predictions=pd.read_csv(ROOT/'reports/bms/predictions.csv')
        metrics=pd.read_csv(ROOT/'reports/bms/metrics_summary.csv').set_index('model')
        self.assertEqual(features.vehicle.nunique(),20)
        self.assertEqual(len(features),info['sessions'])
        self.assertGreaterEqual(features.reference_sessions.min(),3)
        self.assertFalse(features.duplicated(['vehicle','session']).any())
        self.assertEqual(predictions.groupby('vehicle').fold.nunique().max(),1)
        self.assertEqual(predictions.fold.nunique(),5)
        for name,part in predictions.groupby('model'):
            self.assertEqual(len(part),len(features))
            self.assertFalse(part.duplicated(['vehicle','session']).any())
            self.assertTrue(np.isfinite(part[['reference_soh_pct','prediction']]).all().all())
            scores=[]
            for _,vehicle in part.groupby('vehicle'):
                scores.append([mean_absolute_error(vehicle.reference_soh_pct,vehicle.prediction),
                               np.sqrt(mean_squared_error(vehicle.reference_soh_pct,vehicle.prediction)),
                               r2_score(vehicle.reference_soh_pct,vehicle.prediction)])
            np.testing.assert_allclose(metrics.loc[name,['mae','rmse','r2']].to_numpy(dtype=float),np.mean(scores,axis=0),rtol=1e-8)
    def test_page_modes_and_both_models(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'app/streamlit_app.py'),default_timeout=60).run()
        app.radio(key='navigation').set_value('BMS trên xe').run()
        self.assertFalse(app.exception or app.error)
        for mode in ['Đánh giá theo xe','Nguồn và phương pháp','Dự đoán BMS']:
            app.radio(key='bms_mode').set_value(mode).run()
            self.assertFalse(app.exception or app.error,[e.message for e in app.exception])
        for model in ['Ridge-RF residual','Random Forest']:
            app.selectbox(key='bms_predict_model').set_value(model).run()
            app.button(key='bms_predict').click().run()
            self.assertFalse(app.exception or app.error,[e.message for e in app.exception])
            self.assertTrue(any('SOH SUY RA' in element.value for element in app.markdown))

if __name__=='__main__': unittest.main()

