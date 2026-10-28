"""Regression checks for measured BMS summaries and honest diagnostic boundaries."""
import unittest
from unittest.mock import patch
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from webapp.server import app
from webapp.data import table
from webapp.bms_assessment import assess,read_limits


class AssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frame=table('data/bms/processed/01_example.csv.gz')
        cls.window=frame[frame.time_s<=120].copy()
        cls.client=app.test_client()

    def assessment(self,prediction=91.87,limits=None,outside=None,window=None):
        return assess(self.window if window is None else window,prediction,outside or [],read_limits(limits or {}),{'kind':'example','label':'test'})

    def test_metrics_use_measured_signals_and_nominal_capacity(self):
        a=self.assessment();m=a['metrics']
        self.assertAlmostEqual(m['loss_pct'],8.13)
        self.assertAlmostEqual(m['capacity_ah'],145*.9187)
        self.assertEqual(m['temperature_min_c'],38)
        self.assertEqual(m['temperature_max_c'],41)
        self.assertAlmostEqual(m['cell_spread_max_mv'],19)
        self.assertEqual(m['observed_seconds'],120)
        self.assertEqual([x['status'] for x in a['indicators']],['unset']*3)
        self.assertIn('Chưa đủ dữ liệu',a['fault_status'])

    def test_capacity_reference_is_scoped_not_a_fault_diagnosis(self):
        for value,status in [(79.9,'below'),(80,'at_or_above'),(91.8,'at_or_above'),(101,'review')]:
            a=self.assessment(prediction=value)
            self.assertEqual(a['capacity_reference']['status'],status)
            self.assertEqual(a['capacity_reference']['kind'],'research_reference')
            self.assertIn('Chưa đủ dữ liệu',a['fault_status'])
        a=self.assessment(prediction=91.8,limits={'limit_soh_min':'95','limit_source':'Mốc nghiên cứu thử'})
        self.assertEqual(a['capacity_reference']['status'],'below')
        self.assertEqual(a['capacity_reference']['kind'],'user_criterion')

    def test_range_validation_is_not_a_safety_threshold(self):
        hot=self.window.copy();hot['min_temperature']=78;hot['max_temperature']=80
        a=self.assessment(window=hot)
        self.assertEqual(a['metrics']['temperature_max_c'],80)
        self.assertTrue(all(x['status']=='unset' for x in a['indicators']))
        self.assertIn('chưa có tiêu chí',a['comparison'])

    def test_user_criteria_are_explicit_and_boundary_safe(self):
        equal=self.assessment(limits={'limit_temperature_max':'41','limit_cell_spread_mv':'19','limit_soh_min':'91.87','limit_source':'Tiêu chí thử nghiệm'})
        self.assertTrue(all(x['status']=='within' for x in equal['indicators']))
        crossed=self.assessment(limits={'limit_temperature_max':'40','limit_cell_spread_mv':'15','limit_soh_min':'92','limit_source':'Tiêu chí thử nghiệm'})
        self.assertEqual(len(crossed['alerts']),3)
        self.assertEqual(crossed['level'],'review')
        self.assertIn('đã nhập',crossed['comparison'])

    def test_unphysical_and_above_nominal_values_are_not_silent_clamps(self):
        a=self.assessment(prediction=105)
        self.assertIsNone(a['metrics']['loss_pct'])
        self.assertAlmostEqual(a['metrics']['capacity_ah'],152.25)
        self.assertEqual(a['alerts'][0]['code'],'above_nominal')
        for bad in [-1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):self.assessment(prediction=bad)

    def test_invalid_criteria_rejected_before_loading_model(self):
        for fields in [{'limit_temperature_max':'40'}, {'limit_temperature_max':'NaN','limit_source':'test'}, {'limit_soh_min':'101','limit_source':'test'}]:
            with patch('webapp.server.artifact',side_effect=AssertionError('model must not be loaded')):
                r=self.client.post('/api/bms/predict',data=dict(sample='1',**fields))
            self.assertEqual(r.status_code,400,r.json)

    def test_sample_results_have_report_and_no_invented_fault_label(self):
        r=self.client.post('/api/bms/predict',data={'sample':'1','model':'Random Forest'})
        self.assertEqual(r.status_code,200,r.json)
        a=r.json['assessment']
        self.assertAlmostEqual(r.json['prediction'],91.87241366810775,places=7)
        self.assertGreater(len(a['report_rows']),15)
        self.assertEqual(a['source']['kind'],'example')
        self.assertIn('Chưa đủ dữ liệu',a['fault_status'])
        self.assertFalse(any(x['status']=='within' for x in a['indicators']))
        self.assertLessEqual(max(x['time_s'] for x in r.json['signals']),120)

    def test_selected_vehicle_and_session_are_respected(self):
        data=table('reports/bms/features.csv')
        vehicle=sorted(data.vehicle.unique())[0]
        row=data[data.vehicle==vehicle].sort_values('start').iloc[-1]
        r=self.client.post('/api/bms/predict',data={'sample':'1','sample_vehicle':vehicle,'sample_session':str(int(row.session))})
        self.assertEqual(r.status_code,200,r.json)
        a=r.json['assessment']
        self.assertEqual(a['source']['vehicle'],vehicle)
        self.assertEqual(a['source']['session'],int(row.session))
        self.assertTrue(all(x['month']<str(row.month) for x in a['history']['points']))
        invalid=self.client.post('/api/bms/predict',data={'sample':'1','sample_vehicle':vehicle,'sample_session':'99999999'})
        self.assertEqual(invalid.status_code,400)

    def test_outside_range_is_not_a_confidence_percentage(self):
        a=self.assessment(outside=['temperature_max_mean'])
        self.assertEqual(a['level'],'review')
        self.assertTrue(any(x['code']=='outside' for x in a['alerts']))
        self.assertNotIn('confidence',a)

    def test_valid_uploaded_csv_is_reported_as_upload(self):
        import io
        r=self.client.post('/api/bms/predict',data={'configuration':'BAIC EU500 145Ah',
            'file':(io.BytesIO(self.window.to_csv(index=False).encode()),r'C:\\fakepath\\pack.csv')},content_type='multipart/form-data')
        self.assertEqual(r.status_code,200,r.json)
        self.assertEqual(r.json['assessment']['source']['kind'],'upload')
        self.assertEqual(r.json['assessment']['source']['filename'],'pack.csv')
        self.assertEqual(r.json['assessment']['history']['points'],[])
        self.assertAlmostEqual(r.json['prediction'],91.87241366810775,places=7)

    def test_dense_preview_keeps_temperature_and_imbalance_peaks(self):
        import numpy as np
        from webapp.server import bms_signal_preview
        frame=pd.DataFrame({'time_s':np.linspace(0,120,1001),'max_temperature':30.,'min_temperature':25.,
            'max_cell_voltage':3.7,'min_cell_voltage':3.69})
        frame.loc[501,'max_temperature']=80
        frame.loc[503,'min_temperature']=5
        frame.loc[507,'max_cell_voltage']=4.1
        shown=bms_signal_preview(frame)
        self.assertEqual(shown.max_temperature.max(),80)
        self.assertEqual(shown.min_temperature.min(),5)
        self.assertAlmostEqual((shown.max_cell_voltage-shown.min_cell_voltage).max(),.41)
        self.assertLessEqual(len(shown),306)

    def test_explicit_demo_prediction_matches_held_out_results(self):
        for phase in ['primary','second_life']:
            overview=self.client.get('/api/demo?phase='+phase).json
            chosen=overview['results'][0]
            r=self.client.post('/api/demo/predict',data={'phase':phase,'cycle':str(chosen['cycle'])})
            self.assertEqual(r.status_code,200,r.json)
            self.assertAlmostEqual(r.json['prediction'],chosen['predicted_soh_pct'],places=7)
            self.assertAlmostEqual(r.json['reference'],chosen['soh_pct'],places=7)
            self.assertAlmostEqual(r.json['absolute_error'],chosen['absolute_error'],places=7)
            self.assertNotIn('soh_pct',r.json['features'][0])
            self.assertNotIn('capacity_ah',r.json['features'][0])
            self.assertEqual(r.json['train_batteries'],85)
        self.assertEqual(self.client.post('/api/demo/predict',data={'phase':'primary','cycle':'999999'}).status_code,400)


if __name__=='__main__':unittest.main()
