"""Start Streamlit on Render using the active Python environment."""
import os
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    port = int(os.environ.get("PORT", "8501"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    os.chdir(root)
    os.environ.setdefault("VINCENT_PUBLIC_DEMO", "1")
    for name, value in (("OMP_NUM_THREADS", "2"), ("MKL_NUM_THREADS", "2"), ("OPENBLAS_NUM_THREADS", "1")):
        os.environ.setdefault(name, value)
    args = [sys.executable, "-m", "streamlit", "run", "app/streamlit_app.py",
            "--server.address=0.0.0.0", f"--server.port={port}",
            "--server.headless=true", "--server.fileWatcherType=none",
            "--server.maxUploadSize=20", "--browser.gatherUsageStats=false"]
    os.execv(sys.executable, args)


if __name__ == "__main__":
    main()
