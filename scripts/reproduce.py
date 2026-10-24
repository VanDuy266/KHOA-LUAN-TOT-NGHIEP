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
        ["scripts/build_demo_model.py"],
        ["-m", "pytest", "-q", "--junitxml=reports/pytest-results.xml"],
        ["scripts/build_notebook.py"],
        ["scripts/build_results_notebook.py"],
        ["scripts/build_documents.py"],
    ]
    if (ROOT / "reports/xjtu/features.csv").exists():
        index = next(i for i, command in enumerate(commands) if command[0] == "-m")
        commands[index:index] = [["scripts/evaluate_xjtu.py"], ["scripts/analyze_xjtu.py"], ["scripts/check_xjtu.py"], ["scripts/build_xjtu_documents.py"]]
        commands.append(["scripts/build_midterm.py"])
    for args in commands:
        print("\nĐang chạy: " + " ".join(args), flush=True)
        subprocess.run([sys.executable, *args], cwd=ROOT, env=env, check=True)
    print("Đã tái lập dữ liệu kiểm tra, mô hình, thực nghiệm, notebook và tài liệu.")


if __name__ == "__main__":
    main()
