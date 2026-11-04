"""시간대별/일별 얼굴 수 통계. 화면과 CSV가 같은 함수를 사용한다."""
import csv
import io
from datetime import date, timedelta

from fastapi import HTTPException

from database import get_conn

BASIS = "성공(COMPLETED)한 분석의 얼굴 수만 합산 / 실패 분석과 유효하지 않은 값은 제외 / 같은 고객이 여러 이미지에 있으면 중복 집계될 수 있음"
MAX_DAYS = 366


def _parse_range(start: str, end: str) -> tuple[date, date]:
    try:
        s, e = date.fromisoformat(start), date.fromisoformat(end)
    except ValueError:
        raise HTTPException(400, "날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)")
    if e < s:
        raise HTTPException(400, "종료일이 시작일보다 빠를 수 없습니다.")
    if (e - s).days >= MAX_DAYS:
        raise HTTPException(400, f"조회 기간은 최대 {MAX_DAYS}일입니다.")
    return s, e


def aggregate(user_id: int, start: str, end: str, unit: str) -> dict:
    s, e = _parse_range(start, end)
    if unit not in ("hour", "day"):
        raise HTTPException(400, "집계 단위는 hour 또는 day 입니다.")
    key = "strftime('%H', analyzed_at)" if unit == "hour" else "date(analyzed_at)"
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT {key} AS bucket, SUM(face_count) AS faces, COUNT(*) AS cnt
                FROM analyses
                WHERE user_id = ? AND status = 'COMPLETED' AND face_count IS NOT NULL AND face_count >= 0
                  AND date(analyzed_at) BETWEEN ? AND ?
                GROUP BY bucket""",
            (user_id, s.isoformat(), e.isoformat()),
        ).fetchall()
    found = {r["bucket"]: (r["faces"], r["cnt"]) for r in rows}
    if unit == "hour":
        labels = [f"{h:02d}" for h in range(24)]
        names = [f"{h:02d}:00-{h:02d}:59" for h in range(24)]
    else:
        labels = [(s + timedelta(days=i)).isoformat() for i in range((e - s).days + 1)]
        names = labels
    items = [{"label": n, "faces": found.get(k, (0, 0))[0], "analyses": found.get(k, (0, 0))[1]}
             for k, n in zip(labels, names)]
    return {"start": s.isoformat(), "end": e.isoformat(), "unit": unit, "basis": BASIS,
            "total_faces": sum(i["faces"] for i in items), "total_analyses": sum(i["analyses"] for i in items),
            "items": items}


def to_csv(stats: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    unit_name = "시간대별" if stats["unit"] == "hour" else "일별"
    w.writerow([f"# 기간: {stats['start']} ~ {stats['end']} / 단위: {unit_name}"])
    w.writerow([f"# 집계 기준: {BASIS}"])
    w.writerow(["시간대" if stats["unit"] == "hour" else "날짜", "얼굴 수 합계", "성공 분석 건수"])
    for i in stats["items"]:
        w.writerow([i["label"], i["faces"], i["analyses"]])
    w.writerow(["합계", stats["total_faces"], stats["total_analyses"]])
    return "﻿" + buf.getvalue()  # Excel 한글 깨짐 방지 BOM


def summary(user_id: int) -> dict:
    today = date.today().isoformat()
    with get_conn() as conn:
        r = conn.execute(
            """SELECT
                 COALESCE(SUM(CASE WHEN status='COMPLETED' AND date(analyzed_at)=? THEN face_count END), 0) AS today_faces,
                 COALESCE(SUM(CASE WHEN status='COMPLETED' AND date(analyzed_at)=? THEN 1 END), 0) AS today_completed,
                 COALESCE(SUM(CASE WHEN status='FAILED' AND date(analyzed_at)=? THEN 1 END), 0) AS today_failed,
                 COUNT(*) AS total_analyses
               FROM analyses WHERE user_id = ?""",
            (today, today, today, user_id),
        ).fetchone()
    return dict(r)
