"""Kiểm tra đường upload CSV, gồm dữ liệu tiếng Việt và trường hợp trộn pin."""

from pathlib import Path
import sys
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "src"))
from prediction import read_csv, predict
import joblib


def test_vietnamese_csv_and_original_csv_give_same_prediction():
    original = pd.read_csv(ROOT / "examples/chu_ky_mau_SDU.csv")
    renamed = original.rename(
        columns={
            "time": "Thời gian (giây)",
            "terminal_voltage": "Điện áp (V)",
            "terminal_current": "Dòng điện (A)",
            "temperature": "Nhiệt độ (°C)",
        }
    )
    restored = read_csv(renamed.to_csv(index=False).encode("utf-8-sig"))
    artifact = joblib.load(ROOT / "artifacts/random_forest.joblib")
    first = predict(original, 1, artifact)[0]
    second = predict(restored, 1, artifact)[0]
    assert first == pytest.approx(second)


def test_rejects_multiple_batteries_even_without_cycle_column():
    frame = pd.read_csv(ROOT / "examples/chu_ky_mau_SDU.csv")
    frame["battery"] = ["SDU_01"] * len(frame)
    frame.loc[0, "battery"] = "SDU_02"
    with pytest.raises(ValueError, match="đúng một pin"):
        predict(frame, 1, {})


def test_rejects_mismatched_cycle():
    frame = pd.read_csv(ROOT / "examples/chu_ky_mau_SDU.csv")
    frame["cycle"] = 2
    with pytest.raises(ValueError, match="khớp số chu kỳ"):
        predict(frame, 1, {})


def test_rejects_duplicate_alias_columns():
    with pytest.raises(ValueError, match="Tên cột bị trùng"):
        read_csv("time,Thời gian (giây)\n0,0\n".encode("utf-8"))


def test_batch_keeps_valid_cycles_and_reports_invalid_ones():
    from prediction import predict_batch

    artifact = joblib.load(ROOT / "artifacts/random_forest.joblib")
    good = pd.read_csv(ROOT / "examples/chu_ky_mau_SDU.csv").assign(
        battery="SDU_01", cycle=1
    )
    bad = good.head(2).assign(cycle=2)
    result = predict_batch(pd.concat([good, bad], ignore_index=True), artifact)
    assert result.status.tolist() == ["Thành công", "Không hợp lệ"]
    assert pd.notna(result.predicted_soh_pct.iloc[0])
    assert pd.isna(result.predicted_soh_pct.iloc[1])
    assert result.error.iloc[1]


def test_batch_requires_cycle_and_enforces_limit():
    from prediction import predict_batch

    sample = pd.read_csv(ROOT / "examples/chu_ky_mau_SDU.csv")
    with pytest.raises(ValueError, match="cần cột cycle"):
        predict_batch(sample.drop(columns=["cycle"], errors="ignore"), {})
    many = pd.concat(
        [sample.assign(cycle=i) for i in range(1, 2002)], ignore_index=True
    )
    with pytest.raises(ValueError, match="2000 chu kỳ"):
        predict_batch(many, {})


def test_html_report_escapes_user_data_and_history_deduplicates():
    from result_report import html_report, add_history

    rows = pd.DataFrame(
        [
            {
                "battery": "<script>alert(1)</script>",
                "cycle": 1,
                "predicted_soh_pct": 90.0,
                "status": "Thành công",
            }
        ]
    )
    html = html_report(rows, "19/10/2026", "<img src=x>")
    assert "<script>" not in html and "<img src=x>" not in html
    assert "&lt;script&gt;" in html and "Vincent D" in html
    history = add_history([], rows, "request-1", "file.csv", "t1")
    again = add_history(history, rows, "request-1", "file.csv", "t2")
    assert len(again) == 1 and again[0]["created_at"] == "t2"


def test_batch_does_not_mix_same_cycle_across_phases():
    from prediction import predict_batch

    sample = pd.read_csv(ROOT / "examples/chu_ky_mau_SDU.csv")
    artifact = joblib.load(ROOT / "artifacts/random_forest.joblib")
    rows = predict_batch(
        pd.concat([sample.assign(phase_code=0), sample.assign(phase_code=1)]), artifact
    )
    assert len(rows) == 2 and set(rows.phase_code) == {0, 1}
    assert rows.status.eq("Thành công").all()


def test_upload_accepts_csv_larger_than_old_decimal_5mb_limit():
    sample = pd.read_csv(ROOT / "examples/chu_ky_mau_SDU.csv")
    sample["note"] = ["x" * 5_010_000] + [""] * (len(sample) - 1)
    content = sample.to_csv(index=False).encode()
    assert len(content) > 5_000_000
    assert len(read_csv(content)) == len(sample)


def test_upload_limit_matches_binary_streamlit_setting(monkeypatch):
    import prediction

    assert prediction.MAX_UPLOAD_BYTES == 512 * 1024 * 1024
    monkeypatch.setattr(prediction, "MAX_UPLOAD_BYTES", 10)
    with pytest.raises(ValueError, match="512 MiB"):
        prediction.read_csv(b"a" * 11)


def test_raw_sdu_csv_and_gzip_use_relative_discharge_time():
    import gzip

    source = pd.read_csv(ROOT / "examples/chu_ky_mau_SDU.csv")
    expected = source.copy()
    source = source.rename(
        columns={
            "time": "Test_Time(s)",
            "cycle": "Cycle_Index",
            "battery": "Battery_ID",
            "terminal_voltage": "Voltage(V)",
            "terminal_current": "Current(A)",
            "temperature": "Aux_Temperature_1(C)",
        }
    )
    source["Test_Time(s)"] += 10000
    source["Battery_ID"] = 1
    source = source.drop(columns=["phase_code", "phase"], errors="ignore")
    content = source.to_csv(index=False).encode()
    artifact = joblib.load(ROOT / "artifacts/random_forest.joblib")
    for payload in [content, gzip.compress(content)]:
        actual = read_csv(payload, phase_code=0)
        assert actual.time.min() == pytest.approx(0)
        assert set(actual.battery) == {"SDU_01"}
        assert predict(actual, 1, artifact)[0] == pytest.approx(
            predict(expected, 1, artifact)[0]
        )
    with pytest.raises(ValueError, match="chọn giai đoạn"):
        read_csv(content)
