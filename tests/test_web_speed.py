import unittest
from unittest.mock import patch
import pandas as pd
from webapp.server import app
from webapp.data import evaluation_metrics,evaluation_results

class SpeedTests(unittest.TestCase):
    def test_overview_does_not_load_evaluation_predictions(self):
        with patch("webapp.server.evaluation_results",side_effect=AssertionError("large result loaded")):
            r=app.test_client().get("/api/overview")
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json['model_count'],8)
    def test_bms_input_view_skips_heavy_test_tables(self):
        from webapp.data import table
        def limited(path):
            if path in ['reports/bms/predictions.csv','reports/bms/monthly_reference.csv']:
                raise AssertionError("Unneeded evaluation data loaded")
            return table(path)
        with patch('webapp.server.table',side_effect=limited):
            r=app.test_client().get('/api/bms?view=predict')
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json['recorded_charge_sessions'],len(r.json['sessions']))

    def test_small_summary_agrees_with_full_evaluation(self):
        a=evaluation_metrics().sort_values('model').reset_index(drop=True)
        b=evaluation_results()[0].sort_values('model').reset_index(drop=True)
        pd.testing.assert_frame_equal(a,b)
    def test_unified_results_are_reused(self):
        a=evaluation_results();b=evaluation_results()
        self.assertIs(a,b)

if __name__=="__main__":unittest.main()
