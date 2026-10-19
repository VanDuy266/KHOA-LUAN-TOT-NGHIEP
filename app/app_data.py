"""Đọc theo chu kỳ và cache có giới hạn để kiểm soát bộ nhớ."""

import json
from pathlib import Path
import joblib
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]


@st.cache_data(show_spinner=False, max_entries=20)
def _csv(path, modified):
    return pd.read_csv(path)


def table(relative):
    p = ROOT / relative
    return _csv(str(p), p.stat().st_mtime_ns)


@st.cache_data(show_spinner=False, max_entries=20)
def _json(path, modified):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def metadata(relative):
    p = ROOT / relative
    return _json(str(p), p.stat().st_mtime_ns)


@st.cache_resource(show_spinner=False)
def _model(path, modified):
    return joblib.load(path)


def model():
    p = ROOT / "artifacts/random_forest.joblib"
    result = _model(str(p), p.stat().st_mtime_ns)
    if result.get("dataset") != "SDU":
        raise ValueError("Mô hình chưa khớp SDU")
    return result


@st.cache_data(show_spinner=False, max_entries=12)
def _cycle(path, modified, cycle):
    return pd.read_parquet(path, filters=[("cycle", "=", int(cycle))])


def cycle_measurements(battery, cycle, phase="primary"):
    if phase not in ["primary", "second_life"] or battery not in set(
        table("reports/features.csv").battery
    ):
        raise ValueError("Pin hoặc giai đoạn không hợp lệ")
    p = ROOT / "data/clean/cells" / f"{phase}_{battery}.parquet"
    return _cycle(str(p), p.stat().st_mtime_ns, int(cycle))


PHASES = {"primary": "Sử dụng ban đầu", "second_life": "Tái sử dụng"}
