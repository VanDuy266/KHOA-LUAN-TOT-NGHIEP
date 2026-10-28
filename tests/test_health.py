import io
import unittest
import numpy as np
import pandas as pd
from webapp.health import trend_forecast
from webapp.server import app

class HealthTests(unittest.TestCase):
    def frame(self):return pd.DataFrame({"position":[0,10,20,30,40,50],"soh_pct":[100,98,96,94,92,90]})
    def test_known_linear_crossing(self):
        r=trend_forecast(self.frame(),80)
        self.assertAlmostEqual(r["remaining"],50)
        self.assertAlmostEqual(r["crossing"],100)
        self.assertIsNone(r['soc_pct'])
    def test_reached_is_not_broken(self):
        r=trend_forecast(self.frame(),95)
        self.assertEqual(r['status'],'reached')
        self.assertEqual(r['remaining'],0)
        self.assertIn('không đồng nghĩa',r['message'])
    def test_flat_and_increasing_abstain(self):
        for values in [[90]*6,[90,91,92,93,94,95]]:
            f=self.frame();f.soh_pct=values
            self.assertIsNone(trend_forecast(f)['remaining'])
    def test_distant_crossing_abstains(self):
        f=self.frame();f.soh_pct=[100,99.9,99.8,99.7,99.6,99.5]
        self.assertEqual(trend_forecast(f)['status'],'beyond_horizon')
    def test_duplicate_or_missing_values_rejected(self):
        for column,value in [('position',0),('soh_pct',np.nan)]:
            f=self.frame();f.loc[1,column]=value
            with self.assertRaises(ValueError):trend_forecast(f)
    def test_uses_recent_twenty_points(self):
        f=pd.DataFrame({'position':range(30),'soh_pct':100-np.arange(30)*.5})
        r=trend_forecast(f);self.assertEqual(r['fit_samples'],20)
    def test_api_upload_and_soc(self):
        f=self.frame();f['soc_pct']=50
        r=app.test_client().post('/api/health',data={'kind':'upload','file':(io.BytesIO(f.to_csv(index=False).encode()),'history.csv')})
        self.assertEqual(r.status_code,200,r.json)
        self.assertEqual(r.json['result']['soc_pct'],50)
    def test_sdu_cutoff_excludes_future(self):
        r=app.test_client().post('/api/health',data={'kind':'sdu','battery':'SDU_01','phase':'primary','cutoff':'200'})
        self.assertEqual(r.status_code,200,r.json)
        self.assertTrue(all(x['position']<=200 for x in r.json['result']['points']))
    def test_bms_and_options(self):
        c=app.test_client();self.assertEqual(c.get('/api/health/options').status_code,200)
        r=c.post('/api/health',data={'kind':'bms','vehicle':'BAIC_01'})
        self.assertEqual(r.status_code,200,r.json)
        self.assertEqual(r.json['unit'],'months')
    def test_invalid_threshold_or_empty_pin_rejected(self):
        c=app.test_client()
        for data in [{'kind':'sdu','threshold':'nan'},{'kind':'sdu','battery':'missing'}]:
            self.assertEqual(c.post('/api/health',data=data).status_code,400)

if __name__=='__main__':unittest.main()
