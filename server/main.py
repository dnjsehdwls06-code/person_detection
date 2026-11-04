"""person_detection FastAPI 애플리케이션 서버."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from database import init_db
from routers import analyses, auth, stats, users

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("person_detection")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="person_detection API", lifespan=lifespan)
for r in (auth.router, users.router, analyses.router, stats.router):
    app.include_router(r)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"detail": "입력값이 올바르지 않습니다."})


@app.exception_handler(Exception)
async def unhandled_error(_: Request, exc: Exception):
    # 내부 예외·DB 경로는 로그에만 남기고 사용자에게는 요약만 전달
    log.exception("처리되지 않은 오류")
    return JSONResponse(status_code=500, content={"detail": "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."})


@app.get("/api/health")
def health():
    return {"ok": True}
