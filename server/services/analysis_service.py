"""이미지 분석 흐름: 검증 → 원본 저장 → YOLO 얼굴 검출 → 결과 저장."""
import logging
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
from fastapi import HTTPException

from config import UPLOAD_DIR
from database import get_conn
from services import detector

log = logging.getLogger("person_detection")


def _row_to_dict(row) -> dict:
    return {k: row[k] for k in row.keys() if k != "user_id"}


def _run(user_id: int, image: np.ndarray, image_filename: str, original_name: str, retry_of: int | None) -> dict:
    """검출을 실행하고 성공/실패 결과를 각각 별도 행으로 기록한다."""
    analyzed_at = datetime.now().isoformat(timespec="seconds")
    faces, status, count, reason = [], "COMPLETED", None, None
    try:
        faces = detector.detect_faces(image)
        count = len(faces)
    except Exception:
        log.exception("얼굴 검출 실패")
        status, reason = "FAILED", "AI 분석 중 오류가 발생했습니다. 잠시 후 재분석해 주세요."

    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO analyses (user_id, image_filename, original_name, face_count, status,
                                     failure_reason, retry_of, analyzed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, image_filename, original_name, count, status, reason, retry_of, analyzed_at),
        )
        analysis_id = cur.lastrowid
    if status == "COMPLETED":
        detector.save_image(UPLOAD_DIR / f"result_{analysis_id}.jpg", detector.draw_boxes(image, faces))
    return {**get_analysis(user_id, analysis_id), "faces": faces}


def analyze_upload(user_id: int, image: np.ndarray, original_name: str) -> dict:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    image_filename = f"{uuid.uuid4().hex}.jpg"
    detector.save_image(UPLOAD_DIR / image_filename, image)
    return _run(user_id, image, image_filename, Path(original_name).name, None)


def reanalyze(user_id: int, analysis_id: int) -> dict:
    """실패한 분석을 다시 실행한다. 기존 행은 그대로 두고 새 이력을 만든다."""
    src = get_analysis(user_id, analysis_id)
    if src["status"] != "FAILED":
        raise HTTPException(400, "실패한 분석만 재분석할 수 있습니다.")
    image = detector.load_image(UPLOAD_DIR / src["image_filename"])
    if image is None:
        raise HTTPException(400, "원본 이미지가 없어 재분석할 수 없습니다.")
    return _run(user_id, image, src["image_filename"], src["original_name"], analysis_id)


def get_analysis(user_id: int, analysis_id: int) -> dict:
    # user_id 조건으로 다른 사용자의 분석은 존재하지 않는 것처럼 처리
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM analyses WHERE id = ? AND user_id = ?", (analysis_id, user_id)).fetchone()
    if not row:
        raise HTTPException(404, "분석 결과를 찾을 수 없습니다.")
    return _row_to_dict(row)


def list_analyses(user_id: int, start: str | None, end: str | None, order: str, limit: int) -> list[dict]:
    sql = "SELECT * FROM analyses WHERE user_id = ?"
    params: list = [user_id]
    if start:
        sql += " AND date(analyzed_at) >= ?"
        params.append(start)
    if end:
        sql += " AND date(analyzed_at) <= ?"
        params.append(end)
    sql += " ORDER BY analyzed_at " + ("ASC" if order == "asc" else "DESC") + ", id " + ("ASC" if order == "asc" else "DESC")
    sql += " LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        return [_row_to_dict(r) for r in conn.execute(sql, params).fetchall()]
