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


class FriendlyColumnNamesTests(unittest.TestCase):
    def test_vietnamese_names_and_units_are_suggested_without_changing_values(self):
        raw="Thoi gian(ms),Dien ap(mV),Dong dien(mA),Nhiet do(K)\n0,3300,-1000,298.15\n60000,3250,-1000,298.25\n120000,3200,-1000,298.35\n".encode()
        response=app.test_client().post('/api/column-mapping/preview',data={'file':(io.BytesIO(raw),'pin.csv')})
        self.assertEqual(response.status_code,200)
        data=response.json
        self.assertTrue(all(data['suggestions'].values()))
        self.assertEqual(data['suggested_units'],dict(time='ms',terminal_voltage='mV',terminal_current='mA',temperature='K'))
        result=normalize(raw,data['suggestions'],data['suggested_units'])
        self.assertEqual(result.time.tolist(),[0,60,120])
        self.assertAlmostEqual(result.terminal_voltage.iloc[0],3.3)
        self.assertAlmostEqual(result.temperature.iloc[0],25)

    def test_missing_signal_is_not_fabricated(self):
        raw=b"time,Voltage(V),Current(A)\n0,4,-2\n120,3.9,-2\n"
        response=app.test_client().post('/api/column-mapping/preview',data={'file':(io.BytesIO(raw),'missing.csv')})
        self.assertEqual(response.json['suggestions']['temperature'],'')

    def test_group_identity_can_be_read_from_vietnamese_headers(self):
        raw="Mã pin,Chu kỳ,Giai đoạn,Thời gian (s),Điện áp (V),Dòng điện (A),Nhiệt độ (C)\nPIN-A,2,0,0,4,-2,25\nPIN-A,2,0,120,3.9,-2,25\n".encode()
        response=app.test_client().post('/api/column-mapping/preview',data={'file':(io.BytesIO(raw),'data.csv')})
        self.assertEqual(response.json['context_values']['battery'],'PIN-A')
        self.assertEqual(response.json['context_columns']['cycle'],'Chu kỳ')

    def test_vietnamese_group_names_do_not_allow_multiple_pins_to_be_merged(self):
        raw="Mã pin,Chu kỳ,Giai đoạn,Thời gian (s),Điện áp (V),Dòng điện (A),Nhiệt độ (C)\nPIN-A,1,0,0,4,-2,25\nPIN-B,1,0,120,3.9,-2,25\n".encode()
        from werkzeug.datastructures import FileStorage
        from webapp.upload_table import read_upload
        with self.assertRaisesRegex(ValueError,'nhiều pin'):
            read_upload(FileStorage(stream=io.BytesIO(raw),filename='data.csv'))

    def test_ambiguous_signal_names_require_a_choice(self):
        raw=b"time,Voltage,terminal_voltage,Current,Temperature\n0,4.1,3.9,-2,25\n120,4,3.8,-2,25\n"
        response=app.test_client().post('/api/column-mapping/preview',data={'file':(io.BytesIO(raw),'ambiguous.csv')})
        self.assertEqual(response.json['suggestions']['terminal_voltage'],'')
