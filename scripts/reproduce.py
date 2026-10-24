"""Chạy lần lượt các bước tái lập; dừng ngay nếu một bước lỗi."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    env = os.environ.copy()
    env.setdefault("OMP_NUM_THREADS", "2")
    env.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
    commands = [
        ["scripts/check_dataset.py"],
        ["scripts/run_experiment.py"],
        ["scripts/train_gru.py"],
        ["scripts/analyze_results.py"],
        ["scripts/save_models.py"],
        ["scripts/analyze_anomalies.py"],
        ["scripts/evaluate_hybrid.py"],
        ["-m", "pytest", "-q", "--junitxml=reports/pytest-results.xml"],
        ["scripts/build_notebook.py"],
        ["scripts/build_documents.py"],
    ]
    for args in commands:
        print("\nĐang chạy: " + " ".join(args), flush=True)
        subprocess.run([sys.executable, *args], cwd=ROOT, env=env, check=True)
    print("Đã tái lập dữ liệu kiểm tra, mô hình, thực nghiệm, notebook và tài liệu.")


if __name__ == "__main__":
    main()
