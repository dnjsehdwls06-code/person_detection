"""환경변수 기반 설정값."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
SERVER_DIR = ROOT_DIR / "server"

load_dotenv(ROOT_DIR / ".env")

def _path(name: str, default: str) -> Path:
    # 상대 경로는 프로젝트 루트 기준으로 해석
    p = Path(os.getenv(name) or default)
    return p if p.is_absolute() else ROOT_DIR / p


DB_PATH = _path("DB_PATH", "database/database.db")
SCHEMA_PATH = ROOT_DIR / "database" / "schema.sql"
UPLOAD_DIR = _path("UPLOAD_DIR", "server/uploads")
MODEL_PATH = _path("MODEL_PATH", "server/models/yolov8n-face.pt")

CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.35"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
TOKEN_HOURS = int(os.getenv("TOKEN_HOURS", "12"))
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "BMP"}
ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
