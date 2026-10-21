import sys
import unittest
import gzip
import io
from unittest.mock import patch
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "src"))
from input_audit import audit_frame
from prediction import read_csv


class InputAuditTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({
            "battery": ["pin-test"] * 5, "cycle": [1] * 5, "phase_code": [0] * 5,
            "time": [0, 30, 60, 90, 120], "terminal_voltage": [4.1, 4, 3.9, 3.8, 3.7],
            "terminal_current": [-0.5] * 5, "temperature": [25.0] * 5,
        })

    def test_valid_and_missing_columns(self):
        _, checks, issue = audit_frame(self.frame)
        self.assertFalse(issue)
        self.assertEqual(checks.status.tolist(), ["Hợp lệ"])
        schema, checks, issue = audit_frame(self.frame.drop(columns="temperature"))
        self.assertIn("temperature", issue)
        self.assertTrue(checks.empty)
        self.assertFalse(schema[schema["Cột"] == "temperature"]["Có trong file"].iloc[0])

    def test_bad_group_does_not_hide_valid_group(self):
        bad = self.frame.copy()
        bad["cycle"] = 2
        bad.loc[0, "temperature"] = float("inf")
        _, checks, issue = audit_frame(pd.concat([self.frame, bad]))
        self.assertFalse(issue)
        self.assertEqual(checks.status.tolist(), ["Hợp lệ", "Không hợp lệ"])

    def test_invalid_identifiers_reported(self):
        self.frame.loc[0, "cycle"] = -1
        _, _, issue = audit_frame(self.frame)
        self.assertIn("1 dòng", issue)

    def test_screen_sample_and_stale_results(self):
        app = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=60).run()
        app.radio(key="navigation").set_value("Kiểm tra file đầu vào").run()
        app.checkbox(key="audit_sample").check().run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(len(app.metric), 3)
        app.checkbox(key="audit_sample").uncheck().run()
        self.assertFalse(app.metric)

    def test_csv_delimiters_encoding_and_case(self):
        for separator, encoding, compressed in [(";", "utf-8-sig", False), ("\t", "utf-16", False), (",", "utf-8", True)]:
            renamed = self.frame.rename(columns=str.upper)
            content = renamed.to_csv(index=False, sep=separator).encode(encoding)
            restored = read_csv(gzip.compress(content) if compressed else content)
            _, checks, issue = audit_frame(restored)
            self.assertFalse(issue)
            self.assertEqual(checks.status.tolist(), ["Hợp lệ"])
        content = self.frame.to_csv(index=False, sep=";", decimal=",").encode()
        restored = read_csv(content)
        self.assertAlmostEqual(restored.terminal_voltage.iloc[0], 4.1)

    def test_upload_is_automatically_checked_and_replaced(self):
        first = io.BytesIO(self.frame.to_csv(index=False).encode())
        first.name = "first.csv"
        with patch("streamlit.file_uploader", return_value=first):
            app = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=60).run()
            app.radio(key="navigation").set_value("Kiểm tra file đầu vào").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[1].value, "1")
            self.assertTrue(any("first.csv" in item.value for item in app.markdown))
        broken = self.frame.drop(columns="temperature")
        second = io.BytesIO(broken.to_csv(index=False, sep=";").encode())
        second.name = "second.csv"
        with patch("streamlit.file_uploader", return_value=second):
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[1].value, "0")
            self.assertTrue(any("temperature" in item.value for item in app.warning))
            self.assertTrue(any("second.csv" in item.value for item in app.markdown))

    def test_missing_and_invalid_values_counted_separately(self):
        self.frame.loc[0, "temperature"] = float("nan")
        self.frame.loc[1, "temperature"] = float("inf")
        schema, checks, _ = audit_frame(self.frame)
        column = schema[schema["Cột"] == "temperature"].iloc[0]
        self.assertEqual(column["Giá trị thiếu"], 1)
        self.assertEqual(column["Không phải số hoặc vô hạn"], 1)
        self.assertEqual(checks.status.tolist(), ["Không hợp lệ"])

    def test_original_sdu_headers_and_time_conversion(self):
        raw = self.frame.rename(columns={
            "time": "test_time(s)", "cycle": "cycle_index", "battery": "battery_id",
            "terminal_voltage": "voltage(v)", "terminal_current": "current(a)",
            "temperature": "aux_temperature_1(c)",
        }).drop(columns="phase_code")
        raw["battery_id"] = 7
        raw["test_time(s)"] += 1000
        restored = read_csv(raw.to_csv(index=False, sep=";").encode(), phase_code=1)
        self.assertEqual(restored.battery.unique().tolist(), ["SDU_07"])
        self.assertEqual(restored.time.tolist(), [0, 30, 60, 90, 120])
        self.assertEqual(restored.phase_code.unique().tolist(), [1])
        _, checks, issue = audit_frame(restored)
        self.assertFalse(issue)
        self.assertEqual(checks.status.tolist(), ["Hợp lệ"])


if __name__ == "__main__":
    unittest.main()
