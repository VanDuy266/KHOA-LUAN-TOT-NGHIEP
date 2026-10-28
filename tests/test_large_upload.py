import io,json,tempfile,unittest
from unittest.mock import patch
import pandas as pd
from werkzeug.datastructures import FileStorage
from webapp.server import app
from webapp.upload_table import read_upload,carry_context

class LargeUploadTests(unittest.TestCase):
    def upload(self,raw):return FileStorage(stream=io.BytesIO(raw),filename='data.csv')
    def test_multiple_groups_need_filter(self):
        raw=b'battery,cycle,time,v,i,t\nA,7,0,4,-1,25\nB,7,60,3.9,-1,25\n'
        with self.assertRaisesRegex(ValueError,'pin/chu'):
            read_upload(self.upload(raw),needed=['time','v','i','t'])
    def test_filter_and_context_are_preserved(self):
        raw=b'battery,cycle,phase_code,time,v,i,t\nA,7,1,0,4,-1,25\nA,7,1,60,3.9,-1,25\nB,8,0,0,4,-1,25\n'
        data=dict(file=(io.BytesIO(raw),'data.csv'),mapping=json.dumps(dict(time='time',terminal_voltage='v',terminal_current='i',temperature='t')),units=json.dumps(dict(time='s',terminal_voltage='V',terminal_current='A',temperature='C')),filter_battery_column='battery',filter_battery_value='A',filter_cycle_column='cycle',filter_cycle_value='7',filter_phase_column='phase_code',filter_phase_value='1')
        r=app.test_client().post('/api/column-mapping/normalize',data=data)
        self.assertEqual(r.status_code,200,r.get_json())
        df=pd.read_csv(io.StringIO(r.get_json()['csv']))
        self.assertEqual(df.cycle.tolist(),[7,7])
        self.assertEqual(df.phase_code.tolist(),[1,1])
        self.assertEqual(df.battery.tolist(),['A','A'])
    def test_csv_over_20mib_can_be_previewed_and_filtered(self):
        with tempfile.TemporaryFile() as stream:
            stream.write(b'battery,cycle,time,v,i,t,note\nA,7,0,4,-1,25,x\nA,7,60,3.9,-1,25,x\n')
            block=b'B,8,0,4,-1,25,'+b'x'*1024+b'\n'
            for _ in range(22000):stream.write(block)
            self.assertGreater(stream.tell(),20*1024*1024)
            stream.seek(0)
            upload=FileStorage(stream=stream,filename='measurements_all.csv')
            self.assertEqual(len(read_upload(upload,preview=True)),5)
            frame=read_upload(upload,needed=['time','v','i','t'],filters={'battery':'A','cycle':'7'})
            self.assertEqual(len(frame),2)
            self.assertEqual(frame.attrs['scanned_rows'],22002)
    def test_expanded_limit_is_enforced(self):
        raw=b'time,v,i,t\n0,4,-1,25\n60,3.9,-1,25\n'
        with patch('webapp.upload_table.MAX_EXPANDED_BYTES',10),self.assertRaises(ValueError):read_upload(self.upload(raw),preview=True)
    def test_json_multigroup_cannot_be_merged(self):
        raw=b'[{"battery":"A","time":0},{"battery":"B","time":1}]'
        with self.assertRaises(ValueError):read_upload(FileStorage(stream=io.BytesIO(raw),filename='data.json'))
