from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from services import stats_service
from services.auth_service import current_user

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
def stats(start: str, end: str, unit: Literal["hour", "day"] = "hour", user: dict = Depends(current_user)):
    return stats_service.aggregate(user["id"], start, end, unit)


@router.get("/summary")
def summary(user: dict = Depends(current_user)):
    return stats_service.summary(user["id"])


@router.get("/export.csv")
def export_csv(start: str, end: str, unit: Literal["hour", "day"] = "hour", user: dict = Depends(current_user)):
    data = stats_service.aggregate(user["id"], start, end, unit)
    filename = f"face_stats_{unit}_{data['start']}_{data['end']}.csv"
    return Response(stats_service.to_csv(data), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
