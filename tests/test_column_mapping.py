import io,json,unittest
from webapp.server import app
from webapp.column_mapping import normalize

RAW=b"Time,Voltage_measured,Current_measured,Temperature_measured\n1000,4000,1000,298.15\n2000,3900,1100,299.15\n"
M=dict(time="Time",terminal_voltage="Voltage_measured",terminal_current="Current_measured",temperature="Temperature_measured")
U=dict(time="ms",terminal_voltage="mV",terminal_current="mA",temperature="K")
class ColumnMappingTests(unittest.TestCase):
    def test_explicit_units_and_sign(self):
        r=normalize(RAW,M,U,True)
        self.assertEqual(r.time.tolist(),[0,1])
        self.assertEqual(r.terminal_voltage.tolist(),[4,3.9])
        self.assertEqual(r.terminal_current.tolist(),[-1,-1.1])
        self.assertAlmostEqual(r.temperature.iloc[0],25)
    def test_preview_does_not_claim_domain(self):
        r=app.test_client().post('/api/column-mapping/preview',data={'file':(io.BytesIO(RAW),'data.csv')})
        self.assertEqual(r.status_code,200)
        d=r.get_json()
        self.assertEqual(d['suggestions']['terminal_voltage'],'Voltage_measured')
        self.assertEqual(len(d['preview']),2)
    def test_duplicate_mapping_is_rejected(self):
        bad=dict(M,terminal_current=M['terminal_voltage'])
        with self.assertRaises(ValueError):normalize(RAW,bad,U)
    def test_unsorted_time_is_not_silently_repaired(self):
        bad=RAW.replace(b'2000,',b'500,')
        with self.assertRaises(ValueError):normalize(bad,M,U)
    def test_timestamp_requires_conversion(self):
        bad=RAW.replace(b'1000,',b'2021-01-01T00:00:00,',1)
        with self.assertRaises(ValueError):normalize(bad,M,U)
    def test_api_normalizes_but_never_validates_domain(self):
        r=app.test_client().post('/api/column-mapping/normalize',data={'file':(io.BytesIO(RAW),'data.csv'),'mapping':json.dumps(M),'units':json.dumps(U),'positive_discharge':'1'})
        self.assertEqual(r.status_code,200)
        self.assertFalse(r.get_json()['domain_validated'])
        self.assertIn('terminal_voltage',r.get_json()['csv'])
    def test_invalid_unit(self):
        with self.assertRaises(ValueError):normalize(RAW,M,dict(U,time='hours'))
