"""Kho kết quả SQLite cục bộ; không lưu nội dung file tải lên."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data/local/prediction_history.sqlite3"


def save_results(rows, request_id, source, created_at, path=DEFAULT_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=15)) as connection:
        with connection:
            connection.execute("CREATE TABLE IF NOT EXISTS requests (request_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, source TEXT NOT NULL, payload TEXT NOT NULL)")
            connection.execute(
                "INSERT OR IGNORE INTO requests VALUES (?, ?, ?, ?)",
                (request_id, created_at, source, rows.to_json(orient="records", force_ascii=False)),
            )


def load_results(path=DEFAULT_PATH):
    path = Path(path)
    if not path.exists():
        return []
    with closing(sqlite3.connect(path, timeout=15)) as connection:
        exists = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='requests'").fetchone()
        if not exists:
            return []
        requests = connection.execute("SELECT request_id, created_at, source, payload FROM requests ORDER BY rowid DESC").fetchall()
    return [
        {**row, "request_id": request_id, "created_at": created, "source": source}
        for request_id, created, source, payload in requests
        for row in json.loads(payload)
    ]
