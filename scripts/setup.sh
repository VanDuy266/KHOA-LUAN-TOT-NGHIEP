#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export MPLCONFIGDIR="${PWD}/.cache/matplotlib"
export XDG_CACHE_HOME="${PWD}/.cache"
export PIP_CACHE_DIR="${PWD}/.cache/pip"
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
mkdir -p "$MPLCONFIGDIR" "$PIP_CACHE_DIR"
python3 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
.venv/bin/python -m pip install --disable-pip-version-check -r requirements-deep.txt
if [ ! -f data/clean/cells/primary_SDU_01.parquet ]; then
    .venv/bin/python scripts/download_data.py
    .venv/bin/python scripts/prepare_data.py
fi
.venv/bin/python scripts/reproduce.py
