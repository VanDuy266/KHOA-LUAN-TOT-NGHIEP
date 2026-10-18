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
    original = pd.read_csv(ROOT / "examples/chu_ky_mau_B0005.csv")
    renamed = original.rename(columns={"time": "Thời gian (giây)", "terminal_voltage": "Điện áp (V)",
        "terminal_current": "Dòng điện (A)", "temperature": "Nhiệt độ (°C)"})
    restored = read_csv(renamed.to_csv(index=False).encode("utf-8-sig"))
    artifact = joblib.load(ROOT / "artifacts/random_forest.joblib")
    first = predict(original, 1, artifact)[0]
    second = predict(restored, 1, artifact)[0]
    assert first == pytest.approx(second)


def test_rejects_multiple_batteries_even_without_cycle_column():
    frame = pd.read_csv(ROOT / "examples/chu_ky_mau_B0005.csv")
    frame["battery"] = ["B0005"] * len(frame)
    frame.loc[0, "battery"] = "B0006"
    with pytest.raises(ValueError, match="đúng một pin"):
        predict(frame, 1, {})


def test_rejects_mismatched_cycle():
    frame = pd.read_csv(ROOT / "examples/chu_ky_mau_B0005.csv")
    frame["cycle"] = 2
    with pytest.raises(ValueError, match="khớp số chu kỳ"):
        predict(frame, 1, {})


def test_rejects_duplicate_alias_columns():
    with pytest.raises(ValueError, match="Tên cột bị trùng"):
        read_csv("time,Thời gian (giây)\n0,0\n".encode("utf-8"))
