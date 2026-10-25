"""Start Streamlit on Render using the active Python environment."""
import os
import re
from html import escape
from pathlib import Path
import sys



def preview_html(html):
    """Include the thesis title in server HTML for crawlers that do not run JS."""
    title = "Vincent D | Phân tích sức khỏe pin xe điện"
    description = "Vincent D · Tra cứu dữ liệu pin, đánh giá mô hình và dự đoán SOH."
    html = re.sub(r"<title>.*?</title>", "<title>" + escape(title) + "</title>", html, count=1, flags=re.S)
    html = re.sub(r"<!-- vincent-preview -->.*?<!-- /vincent-preview -->", "", html, flags=re.S)
    tags = '<!-- vincent-preview -->\n'
    for attribute, name, value in [
        ("name", "description", description),
        ("property", "og:title", title),
        ("property", "og:description", description),
        ("property", "og:type", "website"),
        ("property", "og:site_name", "Vincent D"),
        ("name", "twitter:card", "summary"),
        ("name", "twitter:title", title),
        ("name", "twitter:description", description),
    ]:
        tags += f'<meta {attribute}="{name}" content="{escape(value, quote=True)}" />\n'
    tags += '<!-- /vincent-preview -->'
    return html.replace('</head>', tags + '</head>', 1)


def configure_link_preview():
    import streamlit
    index = Path(streamlit.__file__).resolve().parent / "static" / "index.html"
    html = index.read_text(encoding="utf-8")
    updated = preview_html(html)
    if updated != html:
        index.write_text(updated, encoding="utf-8")


def main():
    root = Path(__file__).resolve().parents[1]
    port = int(os.environ.get("PORT", "8501"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    os.chdir(root)
    configure_link_preview()
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
