"""사용자 정보 관리 (등록 / 조회 / 수정 / 삭제)."""
import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from database import get_conn, hash_password
from services.auth_service import current_user, verify_password

router = APIRouter(prefix="/api/users", tags=["users"])


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=4, max_length=100)
    display_name: str = Field(min_length=1, max_length=30)


class ProfileIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=30)


class PasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=4, max_length=100)


@router.post("", status_code=201)
def register(body: UserIn, _: dict = Depends(current_user)):
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, display_name, created_at) VALUES (?, ?, ?, ?)",
                (body.username, hash_password(body.password), body.display_name, datetime.now().isoformat(timespec="seconds")),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "이미 사용 중인 아이디입니다.")
    return {"ok": True}


@router.put("/me")
def update_profile(body: ProfileIn, user: dict = Depends(current_user)):
    with get_conn() as conn:
        conn.execute("UPDATE users SET display_name = ? WHERE id = ?", (body.display_name, user["id"]))
    return {"ok": True}


@router.put("/me/password")
def change_password(body: PasswordIn, user: dict = Depends(current_user)):
    with get_conn() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user["id"],)).fetchone()
        if not verify_password(body.current_password, row["password_hash"]):
            raise HTTPException(400, "현재 비밀번호가 올바르지 않습니다.")
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(body.new_password), user["id"]))
    return {"ok": True}


@router.delete("/me")
def delete_me(user: dict = Depends(current_user)):
    try:
        with get_conn() as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user["id"],))
    except sqlite3.IntegrityError:
        # 분석 이력이 연결된 사용자는 참조 무결성을 위해 삭제하지 않는다
        raise HTTPException(409, "분석 이력이 있는 계정은 삭제할 수 없습니다.")
    return {"ok": True}
