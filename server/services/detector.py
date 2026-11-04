"""YOLO 얼굴 검출 (yolov8n-face 가중치, COCO person 모델이 아님)."""
import threading
from pathlib import Path

import cv2
import numpy as np

from config import CONF_THRESHOLD, MODEL_PATH

_model = None
_lock = threading.Lock()


def _get_model():
    global _model
    with _lock:
        if _model is None:
            if not MODEL_PATH.exists():
                raise RuntimeError("얼굴 검출 모델 가중치 파일이 없습니다.")
            from ultralytics import YOLO
            _model = YOLO(str(MODEL_PATH))
        return _model


def detect_faces(image: np.ndarray) -> list[dict]:
    """얼굴 bounding box 목록을 반환한다. 얼굴이 없으면 빈 목록(0명)."""
    result = _get_model().predict(image, conf=CONF_THRESHOLD, verbose=False)[0]
    faces = []
    for box in result.boxes:
        x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
        faces.append({"box": [x1, y1, x2, y2], "confidence": round(float(box.conf[0]), 3)})
    return faces


def draw_boxes(image: np.ndarray, faces: list[dict]) -> np.ndarray:
    out = image.copy()
    thickness = max(2, out.shape[1] // 400)
    for i, face in enumerate(faces, 1):
        x1, y1, x2, y2 = face["box"]
        cv2.rectangle(out, (x1, y1), (x2, y2), (40, 200, 255), thickness)
        cv2.putText(out, f"{i} {face['confidence']:.2f}", (x1, max(15, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5 * thickness / 2 + 0.2, (40, 200, 255), max(1, thickness - 1))
    return out


def save_image(path: Path, image: np.ndarray) -> None:
    # cv2.imwrite 는 한글 경로를 처리하지 못하므로 imencode + tofile 사용
    ok, buf = cv2.imencode(".jpg", image)
    if not ok:
        raise RuntimeError("결과 이미지를 저장하지 못했습니다.")
    buf.tofile(str(path))


def load_image(path: Path) -> np.ndarray | None:
    return cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR)
