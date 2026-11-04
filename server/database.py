"""SQLite 연결 및 초기화. 모든 쿼리는 파라미터 바인딩(?)을 사용한다."""
import sqlite3
from datetime import datetime

import bcrypt

from config import DB_PATH, SCHEMA_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def init_db() -> None:
    """스키마를 적용하고 테스트 계정(test/test)이 없으면 만든다."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        exists = conn.execute("SELECT 1 FROM users WHERE username = ?", ("test",)).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO users (username, password_hash, display_name, created_at) VALUES (?, ?, ?, ?)",
                ("test", hash_password("test"), "테스트 사용자", datetime.now().isoformat(timespec="seconds")),
            )


if __name__ == "__main__":
    init_db()
    print(f"DB 초기화 완료: {DB_PATH}")
