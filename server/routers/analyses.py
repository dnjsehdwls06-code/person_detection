from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from config import UPLOAD_DIR
from services import analysis_service
from services.auth_service import current_user
from services.image_validator import validate_image

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


@router.post("")
async def create_analysis(file: UploadFile | None = File(default=None), user: dict = Depends(current_user)):
    if file is None:
        raise HTTPException(400, "분석할 이미지 파일을 선택해 주세요.")
    data = await file.read()
    image = validate_image(file.filename or "", data)
    return analysis_service.analyze_upload(user["id"], image, file.filename)


@router.get("")
def list_analyses(
    start: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    order: Literal["desc", "asc"] = "desc",
    limit: int = Query(default=200, ge=1, le=1000),
    user: dict = Depends(current_user),
):
    if start and end and end < start:
        raise HTTPException(400, "종료일이 시작일보다 빠를 수 없습니다.")
    return analysis_service.list_analyses(user["id"], start, end, order, limit)


@router.get("/{analysis_id}")
def get_analysis(analysis_id: int, user: dict = Depends(current_user)):
    return analysis_service.get_analysis(user["id"], analysis_id)


@router.post("/{analysis_id}/retry")
def retry(analysis_id: int, user: dict = Depends(current_user)):
    return analysis_service.reanalyze(user["id"], analysis_id)


@router.get("/{analysis_id}/image")
def image(analysis_id: int, kind: Literal["result", "original"] = "result", user: dict = Depends(current_user)):
    a = analysis_service.get_analysis(user["id"], analysis_id)
    path = UPLOAD_DIR / (f"result_{analysis_id}.jpg" if kind == "result" and a["status"] == "COMPLETED" else a["image_filename"])
    if not path.exists():
        raise HTTPException(404, "이미지를 찾을 수 없습니다.")
    return FileResponse(path, media_type="image/jpeg")
