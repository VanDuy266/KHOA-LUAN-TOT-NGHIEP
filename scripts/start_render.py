"""Start the standalone web app; preserve the command used by the Render service."""
import os
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    sys.path.insert(0, str(root))
    port = int(os.environ.get("PORT", "8501"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    for name, value in (("OMP_NUM_THREADS", "2"), ("MKL_NUM_THREADS", "2"), ("OPENBLAS_NUM_THREADS", "1")):
        os.environ.setdefault(name, value)
    if sys.platform == "win32":
        from waitress import serve
        from webapp.server import app
        print(f"Vincent D: http://localhost:{port}", flush=True)
        serve(app, host="0.0.0.0", port=port, threads=2, max_request_body_size=20*1024*1024)
    else:
        args = [sys.executable, "-m", "gunicorn", "webapp.server:app", "--bind", f"0.0.0.0:{port}",
                "--workers", "1", "--threads", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
        os.execv(sys.executable, args)


if __name__ == "__main__":
    main()
