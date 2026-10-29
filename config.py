import os
from secrets import token_hex

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY") or token_hex(32)
    DEBUG = os.getenv("FLASK_DEBUG", "false").strip().lower() in {"1", "true", "yes"}
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024
    RTDETR_CONFIDENCE_THRESHOLD = os.getenv("RTDETR_CONFIDENCE_THRESHOLD", "0.5")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "data/uploads")
    PROCESSED_FOLDER = os.getenv("PROCESSED_FOLDER", "data/processed")
    REPORT_FOLDER = os.getenv("REPORT_FOLDER", "data/reports")
