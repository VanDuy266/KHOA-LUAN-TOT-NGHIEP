"""Kiểm tra phân tách pin, tính cộng được của giải thích và giao diện demo."""

import sys
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from explanation import tree_contributions


class DemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifact = joblib.load(ROOT / "artifacts/random_forest_demo.joblib")
        cls.data = pd.read_csv(ROOT / "reports/features.csv")

    def test_training_excludes_both_phases_of_demo_battery(self):
        artifact = self.artifact
        train = self.data[self.data.battery != artifact["held_out_battery"]]
        self.assertNotIn(artifact["held_out_battery"], artifact["batteries"])
        self.assertEqual(set(artifact["batteries"]), set(train.battery))
        self.assertEqual(artifact["n_train"], len(train))
        for feature in artifact["features"]:
            self.assertAlmostEqual(artifact["training_min"][feature], train[feature].min())
            self.assertAlmostEqual(artifact["training_max"][feature], train[feature].max())

    def test_explanation_reconstructs_predictions_in_both_phases(self):
        artifact = self.artifact
        held = self.data[self.data.battery == artifact["held_out_battery"]]
        for _, phase in held.groupby("phase"):
            for index in [0, len(phase) // 2, len(phase) - 1]:
                features = phase.iloc[[index]][artifact["features"]]
                baseline, contributions = tree_contributions(artifact["model"], features)
                prediction = artifact["model"].predict(features)[0]
                np.testing.assert_allclose(baseline + contributions.contribution.sum(), prediction, atol=1e-9)

    def test_demo_renders_and_changes_phase(self):
        app = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=60).run()
        app.radio(key="navigation").set_value("Demo pin giữ riêng").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(len(app.metric), 3)
        app.selectbox[0].set_value("second_life").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(len(app.metric), 3)


if __name__ == "__main__":
    unittest.main()
