"""업로드 이미지 검증: 확장자, 크기, 실제 디코딩 여부를 모두 확인한다."""
import io
from pathlib import Path

import cv2
import numpy as np
from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from config import ALLOWED_EXTS, ALLOWED_FORMATS, MAX_UPLOAD_MB


def validate_image(filename: str, data: bytes) -> np.ndarray:
    """검증을 통과하면 OpenCV BGR 이미지를 돌려주고, 아니면 400 오류를 낸다."""
    if not filename or not data:
        raise HTTPException(400, "분석할 이미지 파일을 선택해 주세요.")
    if Path(filename).suffix.lower() not in ALLOWED_EXTS:
        raise HTTPException(400, "지원하지 않는 파일 형식입니다. (JPG, PNG, WEBP, BMP)")
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(400, f"파일 크기는 {MAX_UPLOAD_MB}MB 이하여야 합니다.")

    # 확장자와 무관하게 실제 이미지인지 확인
    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise HTTPException(400, "이미지 파일을 읽을 수 없습니다. 손상되었거나 이미지가 아닌 파일입니다.")
    if fmt not in ALLOWED_FORMATS:
        raise HTTPException(400, "지원하지 않는 이미지 형식입니다. (JPG, PNG, WEBP, BMP)")

    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(400, "이미지를 디코딩할 수 없습니다.")
    return image
