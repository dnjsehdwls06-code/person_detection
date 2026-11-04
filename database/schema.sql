-- person_detection SQLite 스키마
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    display_name  TEXT    NOT NULL,
    created_at    TEXT    NOT NULL
);

-- 로그인 토큰 (서버 측 세션)
CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT    PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT    NOT NULL
);

-- 분석 이력: 재분석도 새 행으로 저장하고 retry_of 로 원본을 가리킨다
CREATE TABLE IF NOT EXISTS analyses (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    image_filename TEXT    NOT NULL,
    original_name  TEXT    NOT NULL,
    face_count     INTEGER CHECK (face_count IS NULL OR face_count >= 0),
    status         TEXT    NOT NULL CHECK (status IN ('COMPLETED', 'FAILED')),
    failure_reason TEXT,
    retry_of       INTEGER REFERENCES analyses(id) ON DELETE RESTRICT,
    analyzed_at    TEXT    NOT NULL,
    CHECK (status = 'FAILED' OR face_count IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_analyses_user_time ON analyses(user_id, analyzed_at);
