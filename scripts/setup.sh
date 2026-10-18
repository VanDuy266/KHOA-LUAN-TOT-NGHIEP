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
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.lock.txt
.venv/bin/python scripts/download_data.py
.venv/bin/python scripts/prepare_data.py
.venv/bin/python scripts/check_dataset.py
.venv/bin/python scripts/run_experiment.py
.venv/bin/python scripts/analyze_results.py
.venv/bin/python -m pytest -q --junitxml=reports/pytest-results.xml
.venv/bin/python scripts/build_notebook.py
.venv/bin/python scripts/build_documents.py
.venv/bin/python - <<'PY'
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
suites = ET.parse('reports/pytest-results.xml').getroot()
keys = ['tests', 'failures', 'errors', 'skipped']
counts = {key: sum(int(suite.get(key, 0)) for suite in suites.findall('testsuite')) for key in keys}
assert counts['tests'] > 0 and counts['failures'] == counts['errors'] == 0
Path('reports/verification.json').write_text(json.dumps({'utc': datetime.now(timezone.utc).isoformat(), 'pytest': counts, 'notebook_executed': True, 'documents_generated': True}, indent=2) + '\n')
PY
