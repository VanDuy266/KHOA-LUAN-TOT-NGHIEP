import io,json,unittest,hashlib
import pandas as pd
from webapp.server import app
from webapp.external import analyze
from webapp.column_mapping import preview,normalize

class ExternalTests(unittest.TestCase):
    def frame(self,times=(0,60)):
        return pd.DataFrame(dict(time=times,terminal_voltage=[3.3,3.2],terminal_current=[-2.,-2.],temperature=[25.,26.]))
    def test_discharge_segment_is_not_soh(self):
        r=analyze(self.frame(),dict(chemistry='LFP',level='cell',mode='discharge',nominal_ah='10'))
        self.assertAlmostEqual(r['discharged_ah'],2/60)
        self.assertEqual(r['charged_ah'],0)
        self.assertIsNone(r['soh_pct'])
        self.assertIsNone(r['soc_pct'])
    def test_sparse_trace_has_no_charge_integral(self):
        r=analyze(self.frame((0,120)),{})
        self.assertIsNone(r['discharged_ah'])
        self.assertTrue(r['warnings'])
    def test_soc_is_supplied_not_inferred(self):
        self.assertEqual(analyze(self.frame(),{},[90,89])['soc_pct'],89)
        with self.assertRaises(ValueError):analyze(self.frame(),{},[101,90])
    def test_invalid_profile_is_rejected(self):
        for profile in [[],{'nominal_ah':'nan'},{'nominal_ah':0},{'chemistry':'invented'}]:
            with self.subTest(profile=profile),self.assertRaises(ValueError):analyze(self.frame(),profile)
    def test_json_mapping_and_external_api(self):
        records=[dict(time=0,voltage=3.3,current=-2,temperature=25,soc=90),dict(time=60,voltage=3.2,current=-2,temperature=26,soc=89)]
        raw=json.dumps(records).encode()
        m=dict(time='time',terminal_voltage='voltage',terminal_current='current',temperature='temperature')
        u=dict(time='s',terminal_voltage='V',terminal_current='A',temperature='C')
        c=app.test_client()
        r=c.post('/api/column-mapping/normalize',data={'file':(io.BytesIO(raw),'field.json'),'mapping':json.dumps(m),'units':json.dumps(u),'profile':json.dumps(dict(chemistry='LFP',level='cell',mode='discharge',nominal_ah=10)),'soc_column':'soc'})
        self.assertEqual(r.status_code,200,r.get_json())
        d=r.get_json()
        self.assertFalse(d['domain_validated'])
        self.assertEqual(d['analysis']['soc_pct'],89)
        self.assertIsNone(d['analysis']['soh_pct'])
        self.assertEqual(d['analysis']['source_sha256'],hashlib.sha256(raw).hexdigest())
    def test_nested_json_rejected(self):
        with self.assertRaises(ValueError):preview(b'[{"time":0,"x":{"v":1}}]')
    def test_json_bom_supported(self):
        r=preview(b'\xef\xbb\xbf[{"time":0,"v":1}]')
        self.assertIn('time',r['columns'])
