import unittest
import pandas as pd
from webapp.server import app, speed_summary
from webapp.data import artifact, table, MODELS
from battery_soh.features import FEATURES
from explanation import prediction_contributions, explanation_evidence

class ResearchEvidenceTests(unittest.TestCase):
    def test_additive_reconstruction_for_served_models(self):
        x=table("reports/features.csv")[FEATURES].iloc[[80]]
        for name,path in MODELS.items():
            with self.subTest(model=name):
                model=artifact(path)["model"]
                prediction=float(model.predict(x)[0])
                base,effects,_=prediction_contributions(model,x)
                e=explanation_evidence(base,effects,prediction,x)
                self.assertTrue(e["reconstruction_ok"], e)
                self.assertLess(e["reconstruction_error"],.002)
                self.assertEqual(len(e["top_effects"]),3)
    def test_missing_speed_stays_missing(self):
        rows=speed_summary(pd.DataFrame([dict(model="GRU",fit_seconds=1,predict_seconds=None,n_test=10)]))
        self.assertIsNone(rows[0]["predict_ms_per_sample"])
        self.assertEqual(rows[0]["timed_folds"],0)
    def test_speed_is_weighted_by_timed_samples(self):
        rows=speed_summary(pd.DataFrame([dict(model="RF",fit_seconds=1,predict_seconds=.2,n_test=100),dict(model="RF",fit_seconds=3,predict_seconds=.1,n_test=50)]))
        self.assertAlmostEqual(rows[0]["predict_ms_per_sample"],2)
    def test_health_validation_matches_saved_report(self):
        r=app.test_client().get('/api/health/options').get_json()
        self.assertEqual({x["dataset"] for x in r["validation"]},{"SDU","BMS"})
        self.assertTrue(all(x["scored_crossings"]<=x["future_crossings"] for x in r["validation"]))
