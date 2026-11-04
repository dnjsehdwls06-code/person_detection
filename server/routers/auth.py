from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services import auth_service
from services.auth_service import current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginIn):
    token, user = auth_service.login(body.username.strip(), body.password)
    return {"token": token, "user": user}


@router.post("/logout")
def logout(user: dict = Depends(current_user)):
    auth_service.logout(user["token"])
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return {k: v for k, v in user.items() if k != "token"}
