"""로그인 토큰 발급과 현재 사용자 확인."""
import secrets
from datetime import datetime, timedelta

import bcrypt
from fastapi import Header, HTTPException

from config import TOKEN_HOURS
from database import get_conn


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def login(username: str, password: str) -> tuple[str, dict]:
    with get_conn() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user or not verify_password(password, user["password_hash"]):
            raise HTTPException(401, "아이디 또는 비밀번호가 올바르지 않습니다.")
        token = secrets.token_urlsafe(32)
        expires = (datetime.now() + timedelta(hours=TOKEN_HOURS)).isoformat(timespec="seconds")
        conn.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)", (token, user["id"], expires))
    return token, public_user(user)


def logout(token: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def public_user(row) -> dict:
    return {"id": row["id"], "username": row["username"], "display_name": row["display_name"], "created_at": row["created_at"]}


def current_user(authorization: str = Header(default="")) -> dict:
    """FastAPI 의존성: Bearer 토큰으로 로그인 사용자를 찾는다."""
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(401, "로그인이 필요합니다.")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT u.*, s.token, s.expires_at FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?",
            (token,),
        ).fetchone()
    if not row or row["expires_at"] < datetime.now().isoformat(timespec="seconds"):
        raise HTTPException(401, "로그인이 만료되었습니다. 다시 로그인해 주세요.")
    return {**public_user(row), "token": token}
