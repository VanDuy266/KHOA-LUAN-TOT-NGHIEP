"""Đọc file cục bộ có bộ nhớ đệm; chỉ làm mới khi file thay đổi."""
import json
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]


@st.cache_data(show_spinner=False)
def _csv(path, modified):
    return pd.read_csv(path)


def table(relative):
    path = ROOT / relative
    return _csv(str(path), path.stat().st_mtime_ns)


@st.cache_data(show_spinner=False)
def _json(path, modified):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def metadata(relative):
    path = ROOT / relative
    return _json(str(path), path.stat().st_mtime_ns)


@st.cache_resource(show_spinner=False)
def _model(path, modified):
    # Chỉ đọc mô hình do dự án tạo; không nhận file joblib người dùng tải lên.
    return joblib.load(path)


def model():
    path = ROOT / "artifacts/random_forest.joblib"
    return _model(str(path), path.stat().st_mtime_ns)
