import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from history_store import save_results, load_results


class HistoryTests(unittest.TestCase):
    def test_durable_roundtrip_and_duplicate_request(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.sqlite3"
            self.assertEqual(load_results(path), [])
            rows = pd.DataFrame([{"battery": "SDU_01", "cycle": 1, "predicted_soh_pct": 94.2, "status": "Thành công"}])
            save_results(rows, "request-1", "dữ liệu.csv", "21/10/2026 20:00:00", path)
            save_results(rows, "request-1", "dữ liệu.csv", "21/10/2026 20:00:00", path)
            result = load_results(path)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["source"], "dữ liệu.csv")
            self.assertAlmostEqual(result[0]["predicted_soh_pct"], 94.2)
            save_results(rows, "request-2", "khác.csv", "21/10/2026 21:00:00", path)
            self.assertEqual(len(load_results(path)), 2)

    def test_session_history_filters_and_exports(self):
        app = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=60).run()
        app.radio(key="navigation").set_value("Dự đoán SOH").run()
        app.checkbox[0].check().run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        app.radio(key="navigation").set_value("Lịch sử dự đoán").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[0].value), 1)
        app.text_input[0].set_value("not-a-real-battery").run()
        self.assertFalse(app.exception)
        self.assertTrue(app.dataframe[0].value.empty)
        app.text_input[0].set_value("SDU_01").run()
        self.assertEqual(len(app.dataframe[0].value), 1)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.info)

    def test_opt_in_save_and_archive_view(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.sqlite3"
            with patch("history_store.save_results", side_effect=lambda rows, request_id, source, created: save_results(rows, request_id, source, created, path)):
                app = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=60).run()
                app.radio(key="navigation").set_value("Dự đoán SOH").run()
                self.assertFalse(app.checkbox(key="persist_predictions").value)
                app.checkbox[0].check().run()
                app.checkbox(key="persist_predictions").check().run()
                app.button[0].click().run()
                self.assertFalse(app.exception)
                self.assertFalse(app.error)
                self.assertEqual(len(load_results(path)), 1)
            with patch("history_store.load_results", side_effect=lambda: load_results(path)):
                app.radio(key="navigation").set_value("Lịch sử dự đoán").run()
                app.radio(key="history_scope").set_value("Kho trên máy").run()
                self.assertFalse(app.exception)
                self.assertEqual(len(app.dataframe[0].value), 1)

    def test_pagination_and_sorting(self):
        app = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=60).run()
        app.session_state["prediction_history"] = [
            dict(request_id=str(index), battery="SDU_01", cycle=index + 1,
                 phase_code=0, predicted_soh_pct=70.0 + index / 10,
                 status="Thành công", source="sample.csv", created_at="21/10/2026 20:00:00")
            for index in range(61)
        ]
        app.radio(key="navigation").set_value("Lịch sử dự đoán").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[0].value), 50)
        next(widget for widget in app.selectbox if widget.label == "Trang kết quả").set_value(2).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[0].value), 11)
        app.text_input[0].set_value("missing").run()
        self.assertFalse(app.exception)
        self.assertTrue(app.dataframe[0].value.empty)


if __name__ == "__main__":
    unittest.main()
