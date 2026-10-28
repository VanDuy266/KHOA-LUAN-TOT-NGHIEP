import unittest
from webapp.server import app

class CapacityMeasurementTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
    def post(self, **changes):
        data = dict(reference_ah="100", measured_ah="92", comparable="1")
        data.update(changes)
        return self.client.post("/api/capacity-measurement", data=data)
    def test_capacity_ratio(self):
        r=self.post().get_json()
        self.assertEqual(r["soh_pct"],92)
        self.assertEqual(r["loss_pct"],8)
    def test_no_comparability(self):
        self.assertEqual(self.post(comparable="").status_code,400)
    def test_invalid_values(self):
        for value in ("0","-1","nan","inf","bad"):
            with self.subTest(value=value):
                self.assertEqual(self.post(reference_ah=value).status_code,400)
    def test_above_reference_is_not_negative_wear(self):
        r=self.post(measured_ah="110").get_json()
        self.assertTrue(r["above_reference"])
        self.assertIsNone(r["loss_pct"])
