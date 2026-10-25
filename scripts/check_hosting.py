"""Validate deploy assets without retraining or loading all models into RAM."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
required = ["webapp/bms_assessment.py", "webapp/server.py", "webapp/templates/index.html", "webapp/static/app.js", "webapp/static/app.css", "app/streamlit_app.py", "app/assets/vincent-d-logo-avatar.png", "reports/features.csv", "reports/metrics_summary.csv", "reports/metrics_by_battery.csv", "reports/predictions.csv", "reports/dataset_summary.json", "reports/data_audit.csv", "reports/removed_measurements.csv", "artifacts/random_forest.joblib", "artifacts/ridge_residual_forest.joblib", "artifacts/random_forest_demo.joblib", "artifacts/anomaly_iforest.joblib", "data/clean/sample_measurements.csv", "reports/bms/dataset_summary.json", "reports/bms/features.csv", "reports/bms/monthly_reference.csv", "reports/bms/metrics_summary.csv", "reports/bms/metrics_by_vehicle.csv", "reports/bms/predictions.csv", "reports/bms/timings.csv", "data/bms/processed/windows.parquet", "data/bms/processed/01_example.csv.gz", "artifacts/bms/random_forest.joblib", "artifacts/bms/ridge_residual_forest.joblib", "reports/boosting/metadata.json", "reports/boosting/metrics_summary.csv", "reports/boosting/metrics_by_battery.csv", "reports/boosting/predictions.csv", "reports/boosting/timings.csv", "artifacts/boosting/catboost.joblib", "artifacts/boosting/xgboost.joblib"]
missing=[]
for name in required:
    p=ROOT/name
    if not p.exists() and not (p.suffix==".csv" and p.with_suffix(".csv.gz").exists()):missing.append(name)
cells=list((ROOT/"data/clean/cells").glob("*.parquet"))
if len(cells)<172:missing.append("172 SDU cell/phase Parquet files")
if missing:
    print("Missing deployment assets:",*missing,sep="\n");sys.exit(1)
print(f"Hosting assets OK: {len(required)} required paths, {len(cells)} cell/phase files")
