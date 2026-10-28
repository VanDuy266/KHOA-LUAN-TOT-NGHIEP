import unittest,re
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from webapp.server import app
ROOT=Path(__file__).resolve().parents[1]
class FocusedScopeTests(unittest.TestCase):
    def test_navigation_matches_requested_outputs(self):
        html=app.test_client().get('/').get_data(as_text=True)
        nav=html[html.index('<nav'):html.index('</nav>')]
        self.assertEqual(re.findall(r'data-page="([^"]+)"',nav),['overview','check','health','fault','evaluation','profile'])
        self.assertNotIn('nav-research',nav)
    def test_impossible_soh_is_not_a_successful_result(self):
        fake=pd.DataFrame([dict(battery='SDU_01',cycle=1,status='Thành công',predicted_soh_pct=9000.,outside_count=4)])
        with patch('webapp.server.predict_batch',return_value=fake):
            r=app.test_client().post('/api/forecast',data=dict(sample='1',model='Random Forest',cycle='1',phase_code='0'))
        self.assertEqual(r.status_code,200,r.get_json())
        d=r.get_json()
        self.assertEqual(d['results'][0]['status'],'Không xuất dự đoán')
        self.assertIsNone(d['results'][0]['predicted_soh_pct'])
        self.assertIsNone(d['explanation'])
